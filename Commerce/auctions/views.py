from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from .models import User, Listings, Comments, Bids, ListingOwners

# Django form for new listings
class NewListingForm(forms.Form):
    category_choices = Listings._meta.get_field('category').choices
    style = "margin:10px; padding:4px; width:20%;"
    title = forms.CharField(label=False, widget=forms.TextInput(attrs={'style':style, 'placeholder':"Title"}))
    description = forms.CharField(label=False, widget=forms.Textarea(attrs={'style':"margin:10px; padding:4px; width:90%;", 'placeholder':"Description"}))
    starting_bid = forms.IntegerField(label=False, widget=forms.NumberInput(attrs={'style':style, 'placeholder':"Starting Bid ($)"}), min_value=0)
    image = forms.URLField(required=False, label=False, widget=forms.URLInput(attrs={'style':style, 'placeholder':"URL for image of listing"}))
    category = forms.ChoiceField(required=False, label=False, widget=forms.Select(attrs={'style':style}), choices=category_choices)


# Django form for a new bid
class NewBidForm(forms.Form):
    
    bid = forms.IntegerField()

    # allowing the max bid to be specified for each instance of the form so that the placeholder text can be modified
    def __init__(self, *args, **kwargs):
        self.max_bid = kwargs.pop('max_bid', -1)
        super().__init__(*args, **kwargs)
        style = "margin:10px; padding:4px; width:30%;"
        self.fields['bid'].label = False
        if self.max_bid:
            self.fields['bid'].widget = forms.NumberInput(attrs={'style':style, 'placeholder':f'Bid Amount (Current Bid is {self.max_bid})'})
        else:
            self.fields['bid'].widget = forms.NumberInput(attrs={'style':style, 'placeholder':'There are no bids'})

# Django form for a new comment
class NewCommentForm(forms.Form):
    comment = forms.CharField(label=False, widget=forms.Textarea(attrs={'style':"margin:10px; padding:4px; width:90%;", 'placeholder':"Put your comment here."}))

# This method returns a dictionary of all of the generic data that needs to be used with the listing HTML page
def listing_page_data(request, listing_id):
    listing = Listings.objects.get(pk = listing_id)
    if request.user.is_authenticated:
        watchlist_bool = True if listing in request.user.watchlist.all() else False #returns True if the listing is in the user's watchlist, otherwise False
    else:
        watchlist_bool = None
    if Bids.objects.filter(listing = listing_id).count() == 0: #If there are no bids
        max_bid = (listing.starting_bid - 1) # The max bid is the starting bid minus 1 so that the user can bid the starting bid also
    else:
        max_bid = Bids.objects.filter(listing__pk = listing_id).aggregate(Max('amount'))['amount__max'] # Otherwise, the max bid is the maximum of all the bids
        
    current_price = max_bid
    if current_price + 1 == listing.starting_bid:
        current_price += 1
        
    data_dict = {
        "number_of_bids": Bids.objects.filter(listing = listing_id).count(),
        "listing":listing,
        "owner": ListingOwners.objects.get(listing = listing),
        "watchlist_bool": watchlist_bool,
        "new_comment_form": NewCommentForm(),
        "comments": Comments.objects.filter(listing = listing),
        "max_bid": max_bid,
        "max_bid_user": Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None, #Gets the user attributed to the maximum bid ONLY if there are bids on the listing
        "new_bid_form": NewBidForm(max_bid=max_bid),
        "current_price": current_price # This is the current price of the object, similar to max_bid but if there are no bids then it equals the starting bid
        
    }
    return data_dict
        
        
# The index method creates a list of tuples that have the listing name and then its owner
def index(request):
    listings = Listings.objects.all()
    owners = ListingOwners.objects.all()
    current_prices = []
    for listing in listings: # adds each listing's current price to another list
        current_price = listing_page_data(request, listing.id)['current_price']
        current_prices.append(current_price)
    
    return render(request, "auctions/index.html", {
        "listings": list(zip(listings, owners, current_prices)),
        "title": "Active Listings"
    })

# Logs the user in
def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")

# Logs the user out
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

# Registers a user
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

# This method gives a form so the user can create a new listing (it is login required because the user must be signed in in order to sell something)
@login_required
def new_listing(request):
    if request.method == "POST":
        form = NewListingForm(request.POST)
        
        if form.is_valid(): # If the form is valid, saves the new listing and its corresponding owner.

            listing_object = Listings(title=form.cleaned_data["title"], description=form.cleaned_data["description"], starting_bid=form.cleaned_data["starting_bid"], image=form.cleaned_data["image"], category=form.cleaned_data["category"])
            listing_object.save()

            owner = ListingOwners(listing = listing_object, user = request.user)
            owner.save()
            
            return HttpResponseRedirect(reverse("index"))
            
        else:
            return render(request, "auctions/new_listing.html", {
                "form": form
            })
    else:

        return render(request, "auctions/new_listing.html", {
            "form": NewListingForm()
        })

           
# This method displays a specific listing
def listing(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)
    owner = ListingOwners.objects.get(listing = listing)
    page_data = listing_page_data(request, listing_id)
    
    # if there are no bids on the listing, then create the bid form where there is no max bid so that the placeholder says there is no max bid
    if page_data['max_bid'] + 1 == listing.starting_bid:
        page_data["new_bid_form"] = NewBidForm(max_bid = None)
   
    return render(request, "auctions/listings.html", page_data)

# adds (or removes) a specific listing to the user's watchlist
def add_to_watchlist(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)
    user = User.objects.get(pk = request.user.id)
    if listing in user.watchlist.all(): #If the listing is already in the watchlist, remove it. Otherwise, add it.
        user.watchlist.remove(listing)
    else:
        user.watchlist.add(listing)
    return HttpResponseRedirect(reverse("listing", args=[listing_id]))

# deals with a bid once a user enters it
def bid(request, listing_id):
    if request.method == 'POST':
    
        page_data = listing_page_data(request, listing_id)

        listing = Listings.objects.get(pk = listing_id)
        form = NewBidForm(request.POST, max_bid = page_data['max_bid'])
        
        # if there are no bids on the listing, then create the bid form where there is no max bid so that the placeholder says there is no max bid
        if page_data['max_bid'] + 1 == listing.starting_bid:
            form = NewBidForm(request.POST, max_bid = None)
            
        page_data["new_bid_form"] = form
        
        if form.is_valid():
            bid = form.cleaned_data["bid"]
            
            #Check to make sure that the bid is greater than the previous max bid. If it is, save the new bid. Otherwise, render the page again with an error message.
            if bid > page_data['max_bid']: 
                new_bid = Bids(amount = bid, listing = Listings.objects.get(pk=listing_id), bidders = request.user)
                new_bid.save()
                
                return HttpResponseRedirect(reverse("listing", args=[listing_id]))
            else:
                page_data["error_message"] = "Please put in a bid greater than the current bid."
                return render(request, "auctions/listings.html", page_data)
                  
        else:
            return render(request, "auctions/listings.html", page_data)
    else:
        return HttpResponseRedirect(reverse('listing', args=[listing_id]))
        
# This method gets and shows the user's watchlist
@login_required     
def view_watchlist(request):
    watchlist = User.objects.get(pk = request.user.id).watchlist.all()
    listings = []
    for item in watchlist: # creates a list of tuples that contain the item in the watchlist, its owner, and its current price
        current_price = listing_page_data(request, item.id)['current_price']
        listings.append((item, ListingOwners.objects.get(listing = item).user, current_price))
    return render(request, "auctions/index.html", {
        "listings": listings,
        "title": f"{request.user}'s Watchlist"
    })

# This method deals with the comment that a user has entered  
def comment(request, listing_id):
    if request.method == "POST":
    
        page_data = listing_page_data(request, listing_id)
        listing = Listings.objects.get(pk = listing_id)
        
        # if there are no bids on the listing, then create the bid form where there is no max bid so that the placeholder says there is no max bid
        if page_data['max_bid'] + 1 == listing.starting_bid:
            page_data["new_bid_form"] = NewBidForm(max_bid = None)
        
        form = NewCommentForm(request.POST)
        
        # if the form is valid, saves the new comment
        if form.is_valid():
            comment = form.cleaned_data["comment"]
            new_comment = Comments(comment = comment, listing = Listings.objects.get(pk=listing_id), user = request.user)
            new_comment.save()
            return HttpResponseRedirect(reverse("listing", args=[listing_id]))       
        else:
            page_data["new_comment_form"] = form
            return render(request, "auctions/listings.html", page_data)
    else:
        return HttpResponseRedirect(reverse('listing', args=[listing_id]))
        
#closes the listing by making it not active, deleting its category, and removing it from any watchlist
def close_listing(request, listing_id):
    updated_listing = Listings.objects.get(pk=listing_id)
    updated_listing.active = False
    updated_listing.category = "Choose Category"
    updated_listing.save()
    
    users = User.objects.all()
    for user in users:
        if updated_listing in user.watchlist.all():
            user.watchlist.remove(updated_listing)  
    return HttpResponseRedirect(reverse('listing', args=[listing_id]))

# gets all of the categories and renders a HTML page that displays them
def categories(request):
    choices = Listings._meta.get_field('category').choices
    return render(request, "auctions/categories.html", {
        "choices": choices
    })

#displays all of the listings of a specific category
def specific_category(request, category_name):
    listings = Listings.objects.filter(category = category_name.capitalize())
    owners = []
    current_prices = []
    for listing in list(listings): # creates a list of each owner of the listings of the specific category and a list of the current price of each listing of the category
        owners.append(ListingOwners.objects.get(listing = listing))
        current_price = listing_page_data(request, listing.id)['current_price']
        current_prices.append(current_price)
          
    return render(request, "auctions/index.html", {
        "listings": list(zip(listings, owners, current_prices)),
        "title": f"{category_name.capitalize()} Listings"
    })