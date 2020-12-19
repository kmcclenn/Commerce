from django.contrib.auth.models import AbstractUser
from django.db import models


    
class Listings(models.Model):
    title = models.CharField(max_length = 64)
    description = models.TextField()
    starting_bid = models.IntegerField()
    image = models.URLField(blank=True)
    category = models.CharField(max_length = 64, blank=True)
    time_created = models.DateTimeField(auto_now_add = True)
    
    def __str__(self):
        return f"{self.title.capitalize()} (Starting Bid: {self.starting_bid})"
    
    class Meta: 
        verbose_name_plural = 'Listings'

class User(AbstractUser):
    watchlist = models.ManyToManyField(Listings, blank=True, related_name="wishlist_users", default = None)
    
    class Meta: 
        verbose_name_plural = 'Users'
        
        
class ListingOwners(models.Model):
    listing = models.ForeignKey(Listings, on_delete = models.CASCADE, related_name = "owner")
    user = models.ForeignKey(User, on_delete = models.CASCADE, related_name = "listings")
    
    class Meta: 
        verbose_name_plural = 'ListingOwners'
    
    
class Bids(models.Model):
    amount = models.IntegerField()
    listing = models.ForeignKey(Listings, on_delete=models.CASCADE, related_name="bids")
    bidders = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids_made")
    
    class Meta: 
        verbose_name_plural = 'Bids'
        
    def __str__(self):
        return f"${self.amount} Bid on {self.listing} by {self.bidders}"
    
    
class Comments(models.Model):
    comment = models.TextField()
    listing = models.ForeignKey(Listings, on_delete=models.CASCADE, related_name="comments")
    
    class Meta: 
        verbose_name_plural = 'Comments'
