from django.db import models


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"
    OTHER = "O", "Other"


class Category(models.TextChoices):
    GENERAL = "general", "General"
    OBC = "obc", "OBC"
    MBC = "mbc", "MBC"
    SC = "sc", "SC"
    ST = "st", "ST"
    EWS = "ews", "EWS"


class Relationship(models.TextChoices):
    FATHER = "father", "Father"
    MOTHER = "mother", "Mother"
    GUARDIAN = "guardian", "Guardian"


BLOOD_GROUPS = [(g, g) for g in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]]
