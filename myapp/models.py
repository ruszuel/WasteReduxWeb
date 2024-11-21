from django.db import connections
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Users(models.Model):
    profile_picture = models.BinaryField()  
    picture_format = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email_address = models.EmailField(max_length=100, primary_key=True)
    college_department = models.CharField(max_length=50)
    user_password = models.CharField(max_length=100)
    isVerified = models.BooleanField(default=False)
    isFirstTime = models.BooleanField(default=True)
    isSuspended = models.BooleanField(default=False)
    isArchived = models.BooleanField(default=False)
    isWarned = models.BooleanField(default=False)

    class Meta:
        db_table = 'users'
        managed = False


class UnrecognizedImages(models.Model):
    id = models.AutoField(primary_key=True)
    email_address = models.ForeignKey(
        'Users',
        on_delete=models.CASCADE,
        db_column='email_address'
    )
    category = models.CharField(
        max_length=50,
        choices=[
            ('Plastic', 'Plastic'),
            ('Metal', 'Metal'),
            ('Glass', 'Glass')
        ]
    )
    image = models.BinaryField() 
    date_registered = models.DateField()
    isArchived = models.BooleanField(default=False)
    isRecognized = models.BooleanField(default=False)
    isFlagged = models.BooleanField(default=False)
    isAddedToDataset = models.BooleanField(default=False)

    class Meta:
        db_table = 'unrecognized_images'
        managed = False


class ScannedImage(models.Model):
    id = models.AutoField(primary_key=True)
    email_address = models.ForeignKey(
        'Users',
        on_delete=models.CASCADE,
        db_column='email_address'
    )
    image = models.BinaryField()  
    category = models.CharField(
        max_length=50,
        choices=[
            ('Plastic', 'Plastic'),
            ('Metal', 'Metal'),
            ('Glass', 'Glass')
        ]
    )
    location = models.CharField(max_length=100)
    scan_date = models.DateField()
    isArchived = models.BooleanField(default=False)

    class Meta:
        db_table = 'scan_history'
        managed = False


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user.username} Profile'