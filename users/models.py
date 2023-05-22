from django.db import models
from django.contrib.auth.models import User
from PIL import Image


# Extending User Model Using a One-To-One Link
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    avatar = models.ImageField(default="default.jpg", upload_to="profile_images")
    bio = models.TextField()

    def __str__(self):
        return self.user.username

    # resizing images
    def save(self, *args, **kwargs):
        super().save()

        img = Image.open(self.avatar.path)

        if img.height > 100 or img.width > 100:
            new_img = (100, 100)
            img.thumbnail(new_img)
            img.save(self.avatar.path)


from django.db import models
import os
from django.core.files.storage import FileSystemStorage

"""
def upload_to(instance, filename):
    base_path = 'media/uploads'

    if not os.path.exists(base_path):
        os.makedirs(base_path)
    else:
        shutil.rmtree(base_path)
        os.makedirs(base_path)
    return os.path.join(base_path, filename)

"""


def overwrite_upload_to(instance, filename):
    fs = FileSystemStorage()
    if fs.exists(filename):
        fs.delete(filename)
    return filename


class File(models.Model):
    Statement = models.FileField(upload_to=overwrite_upload_to)
    Cheques = models.FileField(upload_to=overwrite_upload_to)
    Direct_Debit = models.FileField(upload_to=overwrite_upload_to)
    EFTs = models.FileField(upload_to=overwrite_upload_to)


class Donor(models.Model):
    name = models.CharField(max_length=100)
    donation = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class StatFile(models.Model):
    pstatement = models.FileField(upload_to=overwrite_upload_to)
