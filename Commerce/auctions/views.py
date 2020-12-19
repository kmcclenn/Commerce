from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from .models import User, Listings, Comments, Bids, ListingOwners

class NewListingForm(forms.Form):
    category_choices = [(None, "Choose Category"), ("Toys", "Toys"), ("Electronics", "Electronics")]
    style = "margin:10px; padding:4px; width:20%;"
    title = forms.CharField(label=False, widget=forms.TextInput(attrs={'style':style, 'placeholder':"Title"}))
    description = forms.CharField(label=False, widget=forms.Textarea(attrs={'style':"margin:10px; padding:4px; width:90%;", 'placeholder':"Description"}))
    starting_bid = forms.IntegerField(label=False, widget=forms.NumberInput(attrs={'style':style, 'placeholder':"Starting Bid ($)"}), min_value=0)
    image = forms.URLField(required=False, label=False, widget=forms.URLInput(attrs={'style':style, 'placeholder':"URL for image of listing"}))
    category = forms.ChoiceField(required=False, label=False, widget=forms.Select(attrs={'style':style}), choices=category_choices)


class NewBidForm(forms.Form):
    
    bid = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        self.max_bid = kwargs.pop('max_bid', -1)
        super().__init__(*args, **kwargs)
        style = "margin:10px; padding:4px; width:20%;"
        self.fields['bid'].label = False
        if self.max_bid:
            self.fields['bid'].widget = forms.NumberInput(attrs={'style':style, 'placeholder':f'Bid Amount (Current Bid is {self.max_bid})'})
        else:
            self.fields['bid'].widget = forms.NumberInput(attrs={'style':style, 'placeholder':'There are no bids'})

class NewCommentForm(forms.Form):
    comment = forms.CharField(label=False, widget=forms.Textarea(attrs={'style':"margin:10px; padding:4px; width:90%;", 'placeholder':"Put your comment here."}))

def listing_page_data(request, listing_id):
    listing = Listings.objects.get(pk = listing_id)
    if request.user.is_authenticated:
        watchlist_bool = True if listing in request.user.watchlist.all() else False
    else:
        watchlist_bool = None
    data_dict = {
        "number_of_bids": Bids.objects.filter(listing = listing_id).count(),
        "listing":listing,
        "owner": ListingOwners.objects.get(listing = listing),
        "watchlist_bool": watchlist_bool,
        "new_comment_form": NewCommentForm(),
        "comments": Comments.objects.filter(listing = listing)
    }
    return data_dict
        
        

def index(request):
    listings = Listings.objects.all()
    owners = ListingOwners.objects.all()
    return render(request, "auctions/index.html", {
        "listings": list(zip(listings, owners)),
        "title": "Active Listings"
    })


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


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


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


@login_required
def new_listing(request):
    if request.method == "POST":
        form = NewListingForm(request.POST)
        if form.is_valid():

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

           

def listing(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)
    owner = ListingOwners.objects.get(listing = listing)
    #if request.user.is_authenticated:
        #watchlist_bool = True if listing in request.user.watchlist.all() else False
    #else:
        #watchlist_bool = None
    #try:
    if Bids.objects.filter(listing = listing_id).count() == 0:
        max_bid = (listing.starting_bid - 1)
    else:
        max_bid = Bids.objects.filter(listing__pk = listing_id).aggregate(Max('amount'))['amount__max']
    #except TypeError:
        #max_bid=1
        
    if max_bid + 1 == listing.starting_bid:
        form = NewBidForm(max_bid = None)
    else:
        form = NewBidForm(max_bid=max_bid)
    page_data = listing_page_data(request, listing_id)
    page_data["new_bid_form"] = form
    page_data["max_bid_user"] = Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None
    return render(request, "auctions/listings.html", page_data)
    
    """
    { listing_page_data(
        "number_of_bids": Bids.objects.filter(listing = listing_id).count(),
        "listing":listing,
        "owner": owner,
        "watchlist_bool": watchlist_bool,
        "new_bid_form": form,
        "max_bid_user": Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None ## I need to make it so the first bid is the actual first bid, not just the starting bid.
    })"""
    
def add_to_watchlist(request, listing_id):
    listing = Listings.objects.get(pk=listing_id)
    user = User.objects.get(pk = request.user.id)
    if listing in user.watchlist.all():  
        user.watchlist.remove(listing)
    else:
        user.watchlist.add(listing)
    return HttpResponseRedirect(reverse("listing", args=[listing_id]))
    
def bid(request, listing_id):
    if request.method == 'POST':
    
        page_data = listing_page_data(request, listing_id)
        
        if Bids.objects.filter(listing = listing_id).count() == 0:
            max_bid = Listings.objects.get(pk=listing_id).starting_bid - 1
        else:
            max_bid = Bids.objects.filter(listing__pk = listing_id).aggregate(Max('amount'))['amount__max']

        listing = Listings.objects.get(pk = listing_id)
        #if request.user.is_authenticated:
            #watchlist_bool = True if listing in request.user.watchlist.all() else False
        #else:
            #watchlist_bool = None
        form = NewBidForm(request.POST, max_bid = max_bid)
        if max_bid + 1 == listing.starting_bid:
            form = NewBidForm(request.POST, max_bid = None)
            
        page_data["new_bid_form"] = form
        page_data["max_bid_user"] = Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None
        
        if form.is_valid():
            bid = form.cleaned_data["bid"]
            if bid > max_bid:
                new_bid = Bids(amount = bid, listing = Listings.objects.get(pk=listing_id), bidders = request.user)
                new_bid.save()
                
                return HttpResponseRedirect(reverse("listing", args=[listing_id]))
            else:
                page_data["error_message"] = "Please put in a bid greater than the current bid."
              
                
                
                return render(request, "auctions/listings.html", page_data)
                """{
                "number_of_bids": Bids.objects.filter(listing = listing_id).count(),
                "listing":Listings.objects.get(pk=listing_id),
                "owner": ListingOwners.objects.get(listing = listing_id),
                "watchlist_bool": watchlist_bool,
                "new_bid_form": form,
                "max_bid_user": Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None,
                "error_message": "Please put in a bid greater than the current bid."
            })"""
            
        else:
            
            return render(request, "auctions/listings.html", page_data)
            """{
                "number_of_bids": Bids.objects.filter(listing = listing_id).count(),
                "listing":Listings.objects.get(pk=listing_id),
                "owner": ListingOwners.objects.get(listing = listing_id),
                "watchlist_bool": watchlist_bool,
                "max_bid_user": Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders  if Bids.objects.filter(listing = listing_id) else None,
                "new_bid_form": form
            })"""
        
    else:
        return HttpResponseRedirect(reverse('listing', args=[listing_id]))
        
        
def view_watchlist(request):
    watchlist = User.objects.get(pk = request.user.id).watchlist.all()
    listings = []
    for item in watchlist:
        listings.append((item, ListingOwners.objects.get(listing = item).user))
    
    return render(request, "auctions/index.html", {
        "listings": listings,
        "title": f"{request.user}'s Watchlist"
    })
    
def comment(request, listing_id):
    if request.method == "POST":
    
        page_data = listing_page_data(request, listing_id)
        listing = Listings.objects.get(pk = listing_id)
        
        
        if Bids.objects.filter(listing = listing_id).count() == 0:
            max_bid = (listing.starting_bid - 1)
        else:
            max_bid = Bids.objects.filter(listing__pk = listing_id).aggregate(Max('amount'))['amount__max']
        if max_bid + 1 == listing.starting_bid:
            bid_form = NewBidForm(max_bid = None)
        else:
            bid_form = NewBidForm(max_bid=max_bid)
            
        page_data["new_bid_form"] = bid_form
        page_data["max_bid_user"] = Bids.objects.filter(listing = listing_id).get(amount = max_bid).bidders if Bids.objects.filter(listing = listing_id) else None
        
        form = NewCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.cleaned_data["comment"]
            
            new_comment = Comments(comment = comment, listing = Listings.objects.get(pk=listing_id), user = request.user)
            new_comment.save()
            
            return HttpResponseRedirect(reverse("listing", args=[listing_id]))
            
        else:
            page_date["new_comment_form"] = NewCommentForm(request.POST)
            return render(request, "auctions/listings.html", page_data)
        
    else:
        return HttpResponseRedirect(reverse('listing', args=[listing_id]))
        
    
