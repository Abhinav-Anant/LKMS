from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
import requests
import json
import base64
from datetime import timedelta
from decimal import Decimal

from .models import LibraryBook, UserBook, Search, LibraryTransaction, BookRequest, CHECKOUT_LIMIT, DUE_DAYS, FINE_PER_DAY
from .serializers import (
    LibraryBookSerializer, UserBookSerializer, UserBookDetailSerializer,
    SearchSerializer, LibraryTransactionSerializer,
    BorrowBookSerializer, ReturnBookSerializer, PurchaseBookSerializer,
    GoogleBooksSearchSerializer, BookSerializer, BookBorrowRecordSerializer,
    BookRequestSerializer, BookRequestCreateSerializer
)

User = get_user_model()

class LibraryBookViewSet(viewsets.ModelViewSet):
    """ViewSet for library books with Google Books integration"""
    queryset = LibraryBook.objects.all()
    serializer_class = LibraryBookSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'isbn', 'category', 'publisher', 'description']
    ordering_fields = ['title', 'author', 'created_at', 'publication_year']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by school for non-superusers
        if not self.request.user.is_superuser:
            user_school = None
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'student_profile') and self.request.user.student_profile.school:
                user_school = self.request.user.student_profile.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
                
            if user_school:
                queryset = queryset.filter(Q(school=user_school) | Q(school__isnull=True))
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
            
        # Filter by availability
        available_only = self.request.query_params.get('available_only')
        if available_only and available_only.lower() == 'true':
            queryset = queryset.filter(available_copies__gt=0)
            
        # Filter by purchasable
        purchasable_only = self.request.query_params.get('purchasable_only')
        if purchasable_only and purchasable_only.lower() == 'true':
            queryset = queryset.filter(saleability=True, price__gt=0)
        
        return queryset

    def perform_create(self, serializer):
        """Set the school automatically based on the authenticated user"""
        user_school = None
        if self.request.user.is_superuser:
            # Superusers can create books for any school or no school
            user_school = serializer.validated_data.get('school')
        else:
            # Regular users create books for their school
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'student_profile') and self.request.user.student_profile.school:
                user_school = self.request.user.student_profile.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
        
        serializer.save(school=user_school)

    @action(detail=False, methods=['get', 'post'])
    def search(self, request):
        """Search books using Google Books API or local library"""
        if request.method == 'GET':
            # Get search parameters
            query = request.query_params.get('q', '')
            offline = request.query_params.get('offline', 'false').lower() == 'true'
            max_results = int(request.query_params.get('max_results', 20))
            start_index = int(request.query_params.get('start_index', 0))
        else:
            # POST method
            serializer = GoogleBooksSearchSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            query = serializer.validated_data['query']
            max_results = serializer.validated_data.get('max_results', 20)
            start_index = serializer.validated_data.get('start_index', 0)
            offline = False

        if not query:
            return Response({'error': 'Query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Save search query
        user_school = None
        if hasattr(request.user, 'school'):
            user_school = request.user.school
        elif hasattr(request.user, 'student_profile') and request.user.student_profile.school:
            user_school = request.user.student_profile.school
        elif hasattr(request.user, 'staff_profile') and request.user.staff_profile.school:
            user_school = request.user.staff_profile.school

        if offline:
            # Search local library
            queryset = self.get_queryset().filter(
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(isbn__icontains=query) |
                Q(description__icontains=query) |
                Q(category__icontains=query)
            )
            
            # Save search
            Search.objects.create(
                user=request.user,
                school=user_school,
                query=query,
                result_count=queryset.count(),
                source='local'
            )
            
            serializer = LibraryBookSerializer(queryset, many=True, context={'request': request})
            return Response({
                'success': True,
                'source': 'local',
                'query': query,
                'total_results': queryset.count(),
                'books': serializer.data
            })
        else:
            # Search Google Books API
            try:
                books_data = self._search_google_books(query, max_results, start_index)
                saved_books = []
                
                for book_data in books_data:
                    # Check if book already exists
                    google_id = book_data.get('google_books_id')
                    book, created = LibraryBook.objects.get_or_create(
                        google_books_id=google_id,
                        defaults={
                            'school': user_school,
                            'title': book_data.get('title', ''),
                            'author': book_data.get('author', ''),
                            'publisher': book_data.get('publisher', ''),
                            'publication_year': book_data.get('publication_year'),
                            'description': book_data.get('description', ''),
                            'category': book_data.get('category', ''),
                            'isbn': book_data.get('isbn', ''),
                            'image_links': book_data.get('image_links', ''),
                            'price': book_data.get('price'),
                            'page_count': book_data.get('page_count'),
                            'audience_type': book_data.get('audience_type', ''),
                            'saleability': book_data.get('saleability', False),
                            'last_search': query,
                            'total_copies': 0,  # Google Books don't have physical copies
                            'available_copies': 0
                        }
                    )
                    
                    if not created:
                        book.last_search = query
                        book.save()
                    
                    saved_books.append(book)
                
                # Save search
                Search.objects.create(
                    user=request.user,
                    school=user_school,
                    query=query,
                    result_count=len(saved_books),
                    source='google'
                )
                
                serializer = LibraryBookSerializer(saved_books, many=True, context={'request': request})
                return Response({
                    'success': True,
                    'source': 'google',
                    'query': query,
                    'total_results': len(saved_books),
                    'books': serializer.data
                })
                
            except Exception as e:
                return Response({
                    'error': f'Google Books API error: {str(e)}'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    def _search_google_books(self, query, max_results=20, start_index=0):
        """Search Google Books API and return formatted book data"""
        api_url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': query,
            'maxResults': min(max_results, 40),
            'startIndex': start_index,
            'printType': 'books'
        }
        
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        books = []
        
        for item in data.get('items', []):
            volume_info = item.get('volumeInfo', {})
            sale_info = item.get('saleInfo', {})
            
            # Extract ISBN
            isbn = ''
            for identifier in volume_info.get('industryIdentifiers', []):
                if identifier.get('type') == 'ISBN_13':
                    isbn = identifier.get('identifier', '')
                    break
                elif identifier.get('type') == 'ISBN_10':
                    isbn = identifier.get('identifier', '')
            
            # Extract price
            price = None
            if sale_info.get('saleability') == 'FOR_SALE':
                list_price = sale_info.get('listPrice', {})
                if list_price.get('amount'):
                    price = Decimal(str(list_price.get('amount')))
            
            book_data = {
                'google_books_id': item.get('id'),
                'title': volume_info.get('title', ''),
                'author': ', '.join(volume_info.get('authors', [])),
                'publisher': volume_info.get('publisher', ''),
                'publication_year': self._extract_year(volume_info.get('publishedDate', '')),
                'description': volume_info.get('description', ''),
                'category': ', '.join(volume_info.get('categories', [])),
                'isbn': isbn,
                'image_links': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                'price': price,
                'page_count': volume_info.get('pageCount'),
                'audience_type': volume_info.get('maturityRating', ''),
                'saleability': sale_info.get('saleability') == 'FOR_SALE'
            }
            books.append(book_data)
        
        return books

    def _extract_year(self, date_string):
        """Extract year from date string"""
        if date_string:
            try:
                return int(date_string.split('-')[0])
            except (ValueError, IndexError):
                pass
        return None

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get recent search suggestions"""
        user_school = None
        if hasattr(request.user, 'school'):
            user_school = request.user.school
        elif hasattr(request.user, 'student_profile') and request.user.student_profile.school:
            user_school = request.user.student_profile.school
        elif hasattr(request.user, 'staff_profile') and request.user.staff_profile.school:
            user_school = request.user.staff_profile.school

        # Get recent searches for user and school
        searches = Search.objects.filter(
            Q(user=request.user) | Q(user__isnull=True, school=user_school)
        ).order_by('-created_at')[:10]
        
        serializer = SearchSerializer(searches, many=True)
        return Response({
            'success': True,
            'suggestions': serializer.data
        })

class UserBookViewSet(viewsets.ModelViewSet):
    """ViewSet for user book relationships (borrowed/purchased)"""
    queryset = UserBook.objects.all()
    serializer_class = UserBookSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['book__title', 'book__author', 'book__isbn']
    ordering_fields = ['created_at', 'borrowed_date', 'due_date']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Students can only see their own books
        if self.request.user.role == 'student':
            queryset = queryset.filter(user=self.request.user)
        # Staff and admin can see all books for their school
        elif not self.request.user.is_superuser:
            user_school = None
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
                
            if user_school:
                queryset = queryset.filter(book__school=user_school)
        
        # Filter by type
        book_type = self.request.query_params.get('type')
        if book_type:
            queryset = queryset.filter(type=book_type.upper())
            
        # Filter by status
        book_status = self.request.query_params.get('status')
        if book_status:
            queryset = queryset.filter(status=book_status)
        
        return queryset

    @action(detail=False, methods=['get'])
    def borrowed(self, request):
        """Get user's borrowed books"""
        queryset = self.get_queryset().filter(type='BORROWED', status='active')
        serializer = UserBookDetailSerializer(queryset, many=True, context={'request': request})
        return Response({
            'success': True,
            'borrowed_books': serializer.data
        })

    @action(detail=False, methods=['get'])
    def purchased(self, request):
        """Get user's purchased books"""
        queryset = self.get_queryset().filter(type='PURCHASED')
        serializer = UserBookDetailSerializer(queryset, many=True, context={'request': request})
        return Response({
            'success': True,
            'purchased_books': serializer.data
        })

    @action(detail=False, methods=['post'])
    def borrow(self, request):
        """Borrow a book"""
        serializer = BorrowBookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        book_id = serializer.validated_data['book_id']
        notes = serializer.validated_data.get('notes', '')

        try:
            book = LibraryBook.objects.get(id=book_id)
        except LibraryBook.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user can borrow books
        if hasattr(request.user, 'balance') and request.user.balance < 0:
            return Response({'error': 'Cannot borrow books due to negative balance'}, status=status.HTTP_403_FORBIDDEN)

        # Check if book is available
        if book.available_copies <= 0:
            return Response({'error': 'Book is not available for borrowing'}, status=status.HTTP_400_BAD_REQUEST)

        # Check checkout limit
        current_borrowed = UserBook.objects.filter(
            user=request.user,
            type='BORROWED',
            status='active'
        ).count()
        
        if current_borrowed >= CHECKOUT_LIMIT:
            return Response({
                'error': f'You have reached the maximum checkout limit of {CHECKOUT_LIMIT} books'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if already borrowed
        if UserBook.objects.filter(user=request.user, book=book, type='BORROWED', status='active').exists():
            return Response({'error': 'You have already borrowed this book'}, status=status.HTTP_400_BAD_REQUEST)

        # Create borrow record
        borrowed_date = timezone.now()
        user_book = UserBook.objects.create(
            user=request.user,
            book=book,
            type='BORROWED',
            borrowed_date=borrowed_date,
            issued_by=request.user  # In self-service, user is the issuer
        )

        # Update book availability
        book.available_copies -= 1
        book.save()

        # Update user's checked_out count if user has this field
        if hasattr(request.user, 'checked_out'):
            request.user.checked_out += 1
            request.user.save()

        serializer = UserBookDetailSerializer(user_book, context={'request': request})
        return Response({
            'success': True,
            'message': 'Book borrowed successfully',
            'user_book': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def return_book(self, request):
        """Return a borrowed book"""
        serializer = ReturnBookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_book_id = serializer.validated_data['user_book_id']
        condition = serializer.validated_data.get('condition', 'good')
        notes = serializer.validated_data.get('notes', '')

        try:
            user_book = UserBook.objects.get(id=user_book_id, user=request.user, type='BORROWED', status='active')
        except UserBook.DoesNotExist:
            return Response({'error': 'Borrowed book record not found'}, status=status.HTTP_404_NOT_FOUND)

        # Calculate fine
        fine_amount = user_book.calculate_fine()
        
        # Update user book record
        user_book.returned_date = timezone.now()
        user_book.fine_amount = fine_amount
        
        if condition == 'good':
            user_book.status = 'returned'
        elif condition == 'damaged':
            user_book.status = 'damaged'
            # Add damage fee (could be configurable)
            damage_fee = Decimal('50.00')  # Example damage fee
            fine_amount += damage_fee
            user_book.fine_amount = fine_amount
        elif condition == 'lost':
            user_book.status = 'lost'
            # Add replacement cost
            replacement_cost = user_book.book.price or Decimal('100.00')  # Default replacement cost
            fine_amount += replacement_cost
            user_book.fine_amount = fine_amount
        
        user_book.save()

        # Update book availability (only if not lost)
        if condition != 'lost':
            user_book.book.available_copies += 1
            user_book.book.save()

        # Deduct fine from user balance if applicable
        if fine_amount > 0 and hasattr(request.user, 'balance'):
            request.user.balance -= fine_amount
            if request.user.balance < 0:
                request.user.is_blocked = True
            request.user.save()

            # Create transaction record
            LibraryTransaction.objects.create(
                user=request.user,
                user_book=user_book,
                transaction_type='fine_payment',
                amount=fine_amount,
                description=f"Fine for returning '{user_book.book.title}' late",
                processed_by=request.user
            )

        # Update user's checked_out count
        if hasattr(request.user, 'checked_out'):
            request.user.checked_out = max(0, request.user.checked_out - 1)
            request.user.save()

        serializer = UserBookDetailSerializer(user_book, context={'request': request})
        return Response({
            'success': True,
            'message': 'Book returned successfully',
            'fine_amount': float(fine_amount),
            'user_book': serializer.data
        })

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """Purchase a book"""
        serializer = PurchaseBookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        book_id = serializer.validated_data['book_id']
        payment_method = serializer.validated_data.get('payment_method', 'balance')

        try:
            book = LibraryBook.objects.get(id=book_id)
        except LibraryBook.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if book is purchasable
        if not book.is_purchasable:
            return Response({'error': 'Book is not available for purchase'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already purchased
        if UserBook.objects.filter(user=request.user, book=book, type='PURCHASED').exists():
            return Response({'error': 'You have already purchased this book'}, status=status.HTTP_400_BAD_REQUEST)

        # Check user balance (for balance payment method)
        if payment_method == 'balance' and hasattr(request.user, 'balance'):
            if request.user.balance < book.price:
                return Response({
                    'error': f'Insufficient balance. Required: ${book.price}, Available: ${request.user.balance}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Create purchase record
        user_book = UserBook.objects.create(
            user=request.user,
            book=book,
            type='PURCHASED',
            purchase_price=book.price
        )

        # Process payment
        if payment_method == 'balance' and hasattr(request.user, 'balance'):
            request.user.balance -= book.price
            request.user.save()

            # Create transaction record
            LibraryTransaction.objects.create(
                user=request.user,
                user_book=user_book,
                transaction_type='book_purchase',
                amount=book.price,
                description=f"Purchase of '{book.title}'",
                processed_by=request.user
            )

        # Update user's purchased count
        if hasattr(request.user, 'purchased'):
            request.user.purchased += 1
            request.user.save()

        serializer = UserBookDetailSerializer(user_book, context={'request': request})
        return Response({
            'success': True,
            'message': 'Book purchased successfully',
            'user_book': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue books"""
        current_time = timezone.now()
        queryset = self.get_queryset().filter(
            type='BORROWED',
            status='active',
            due_date__lt=current_time
        )
        
        serializer = UserBookDetailSerializer(queryset, many=True, context={'request': request})
        return Response({
            'success': True,
            'overdue_books': serializer.data
        })

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for current user"""
        user_books = self.get_queryset()
        
        borrowed_active = user_books.filter(type='BORROWED', status='active').count()
        borrowed_total = user_books.filter(type='BORROWED').count()
        purchased_total = user_books.filter(type='PURCHASED').count()
        overdue_count = user_books.filter(
            type='BORROWED',
            status='active',
            due_date__lt=timezone.now()
        ).count()
        
        total_fines = user_books.filter(fine_amount__gt=0).aggregate(
            total=Sum('fine_amount')
        )['total'] or 0

        return Response({
            'success': True,
            'stats': {
                'borrowed_active': borrowed_active,
                'borrowed_total': borrowed_total,
                'purchased_total': purchased_total,
                'overdue_count': overdue_count,
                'total_fines': float(total_fines),
                'checkout_limit': CHECKOUT_LIMIT,
                'can_borrow_more': borrowed_active < CHECKOUT_LIMIT
            }
        })

# Backward compatibility views
class BookViewSet(LibraryBookViewSet):
    """Backward compatibility for Book model"""
    serializer_class = BookSerializer

class BookBorrowRecordViewSet(UserBookViewSet):
    """Backward compatibility for BookBorrowRecord model"""
    serializer_class = BookBorrowRecordSerializer
    
    def get_queryset(self):
        # Filter to only borrowed books for backward compatibility
        queryset = super().get_queryset()
        return queryset.filter(type='BORROWED')

class LibraryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for library transactions (read-only)"""
    queryset = LibraryTransaction.objects.all()
    serializer_class = LibraryTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'user__email', 'transaction_type', 'description']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Students can only see their own transactions
        if self.request.user.role == 'student':
            queryset = queryset.filter(user=self.request.user)
        # Staff and admin can see all transactions for their school
        elif not self.request.user.is_superuser:
            user_school = None
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
                
            if user_school:
                queryset = queryset.filter(user__student_profile__school=user_school)
        
        return queryset

class SearchViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for search history (read-only)"""
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['query', 'user__username']
    ordering_fields = ['created_at', 'result_count']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Students can only see their own searches and system searches
        if self.request.user.role == 'student':
            user_school = None
            if hasattr(self.request.user, 'student_profile') and self.request.user.student_profile.school:
                user_school = self.request.user.student_profile.school
                
            queryset = queryset.filter(
                Q(user=self.request.user) | 
                Q(user__isnull=True, school=user_school)
            )
        # Staff and admin can see all searches for their school
        elif not self.request.user.is_superuser:
            user_school = None
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
                
            if user_school:
                queryset = queryset.filter(school=user_school)
        
        return queryset


class BookRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing book requests from students"""
    queryset = BookRequest.objects.all()
    serializer_class = BookRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'isbn', 'user__username', 'user__email']
    ordering_fields = ['created_at', 'updated_at', 'urgency', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Students can only see their own requests
        if self.request.user.role == 'student':
            queryset = queryset.filter(user=self.request.user)
        # Staff and admin can see all requests for their school
        elif not self.request.user.is_superuser:
            user_school = None
            if hasattr(self.request.user, 'school'):
                user_school = self.request.user.school
            elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
                user_school = self.request.user.staff_profile.school
                
            if user_school:
                queryset = queryset.filter(school=user_school)
        
        # Filter by status if provided
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by urgency if provided
        urgency = self.request.query_params.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        
        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return BookRequestCreateSerializer
        return BookRequestSerializer

    def perform_create(self, serializer):
        """Set user and school when creating a book request"""
        user_school = None
        
        # Determine user's school
        if hasattr(self.request.user, 'school'):
            user_school = self.request.user.school
        elif hasattr(self.request.user, 'student_profile') and self.request.user.student_profile.school:
            user_school = self.request.user.student_profile.school
        elif hasattr(self.request.user, 'staff_profile') and self.request.user.staff_profile.school:
            user_school = self.request.user.staff_profile.school
        
        serializer.save(user=self.request.user, school=user_school)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a book request (staff/admin only)"""
        if request.user.role not in ['faculty', 'admin', 'librarian']:
            return Response(
                {'error': 'Only staff can approve book requests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        book_request = self.get_object()
        book_request.status = 'approved'
        book_request.reviewed_by = request.user
        book_request.reviewed_at = timezone.now()
        book_request.admin_notes = request.data.get('admin_notes', '')
        book_request.save()
        
        return Response({
            'success': True,
            'message': 'Book request approved successfully',
            'request': BookRequestSerializer(book_request).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a book request (staff/admin only)"""
        if request.user.role not in ['faculty', 'admin', 'librarian']:
            return Response(
                {'error': 'Only staff can reject book requests'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        book_request = self.get_object()
        book_request.status = 'rejected'
        book_request.reviewed_by = request.user
        book_request.reviewed_at = timezone.now()
        book_request.admin_notes = request.data.get('admin_notes', '')
        book_request.save()
        
        return Response({
            'success': True,
            'message': 'Book request rejected',
            'request': BookRequestSerializer(book_request).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_available(self, request, pk=None):
        """Mark a book request as available (staff/admin only)"""
        if request.user.role not in ['faculty', 'admin', 'librarian']:
            return Response(
                {'error': 'Only staff can mark book requests as available'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        book_request = self.get_object()
        library_book_id = request.data.get('library_book_id')
        
        if library_book_id:
            try:
                library_book = LibraryBook.objects.get(id=library_book_id)
                book_request.library_book = library_book
            except LibraryBook.DoesNotExist:
                return Response(
                    {'error': 'Library book not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        book_request.status = 'available'
        book_request.reviewed_by = request.user
        book_request.reviewed_at = timezone.now()
        book_request.admin_notes = request.data.get('admin_notes', '')
        book_request.save()
        
        return Response({
            'success': True,
            'message': 'Book request marked as available',
            'request': BookRequestSerializer(book_request).data
        })