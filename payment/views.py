from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from mycar.models import Product, Profile
import datetime

# Import paypal stuff
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
import uuid  #unique user id for duplicate orders


def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get the order
        order = Order.objects.get(id=pk)
        # Get the order items
        items = OrderItem.objects.filter(order=pk)
        if request.POST:
            status = request.POST['shipping_status']
            # Check if true or false 
            if status == "true":
                # Get the order
                order = Order.objects.filter(id=pk)
                # Update the status
                now = datetime.datetime.now() 
                order.update(shipped=True, date_shipped=now)
            else:
                # Get the order
                order = Order.objects.filter(id=pk)
                # Update the status 
                order.update(shipped=False)
            messages.success(request, "Shipping Status Updated")
            return redirect('home')

        return render(request, 'payment/orders.html', {"order":order, "items":items})

    else:
        messages.success(request, "Access denied!")
        return redirect('home')

    
def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            # Get the order
            order = Order.objects.filter(id=num)
            # grab date and time 
            now = datetime.datetime.now() 
            # update order
            order.update(shipped=True, date_shipped=now)
            # redirect
            messages.success(request, "Shipping Status Updated")
            return redirect('home')

        return render(request,"payment/not_shipped_dash.html",{"orders":orders})
    else:
        messages.success(request, "Access denied!")
        return redirect('home') 

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            # grab the order
            order = Order.objects.filter(id=num)
            # grab date and time 
            now = datetime.datetime.now() 
            # update order
            order.update(shipped=False)
            # redirect
            messages.success(request, "Shipping Status Updated")
            return redirect('home')
        return render(request,"payment/shipped_dash.html",{"orders":orders})
    else:
        messages.success(request, "Access denied!")
        return redirect('home')

def process_order(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        # Get billing from the last page
        payment_form = PaymentForm(request.POST or None)
        # Get shipping session data
        my_shipping = request.session.get('my_shipping')

        # Gather order info
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']

        # Create Shipping Address from session info

        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals

        # Create an order

        if request.user.is_authenticated:
            # logged in
            user = request.user
            # Create orde
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()
            
            # Add oredr items
            # Get the order id

            order_id = create_order.pk

            # get product info
            for product in cart_products():
                # get product id
                product_id = product.id
                # Get product price
                if product.best_offer:
                    price = product.sale_price
                else:
                    price = product.price
                    # Get quantity


                for key, value in quantities().items():
                    if int(key) == product.id:
                            # create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
                        create_order_item.save()

            # Delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    # Delete the key
                    del request.session[key]

            # Delete cart fro database(old_cart field)
            current_user = Profile.objects.filter(user__id=request.user.id)
            # Delete shopping cart in database
            current_user.update(old_cart="")


            messages.success(request, "Order Placed!")
            return redirect('home')
        
        else:
            # not logged in


            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            order_id = create_order.pk


            for product in cart_products():
                # get product id
                product_id = product.id
                # Get product price
                if product.best_offer:
                    price = product.sale_price
                else:
                    price = product.price
                    # Get quantity


                    for key, value in quantities().items():
                        if int(key) == product.id:
                            # create order item
                            create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
                            create_order_item.save()

                # Delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    # Delete the key
                    del request.session[key]

            messages.success(request, "Order Placed!")
            return redirect('home')
        # print(shipping_address)


    else:
        messages.success(request, "Access denied!")
        return redirect('home')


def billing_info(request):
    if request.POST:

        # Get the cart
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        # Create a session with shipping info
        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping
        # Gather order info
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']

        # Create Shipping Address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals

        # Get the host
        host = request.get_host()
        # Create an Invoice number
        my_Invoice = str(uuid.uuid4())

        # Create paypal form dictionary
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': totals,
            'item_name': 'ShopNasi orders',
            'no_shipping': '2',
            'invoice': my_Invoice,
            'currency_code': 'USD',
            'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
            'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
            'cancel_return': 'https://{}{}'.format(host, reverse("payment_failed")),
        }

        # Create actual paypal button
        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        # Check to see if user is logged in
        if request.user.is_authenticated:
            # Get the billing form
            billing_form = PaymentForm()

            # logged in
            user = request.user
            # Create order
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_Invoice)
            create_order.save()

            # Add order items
            # Get the order id
            order_id = create_order.pk

            # get product info
            for product in cart_products():
                # get product id
                product_id = product.id
                # Get product price
                if product.best_offer:
                    price = product.sale_price
                else:
                    price = product.price

                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
                        create_order_item.save()

            # Delete cart from database(old_cart field)
            current_user = Profile.objects.filter(user__id=request.user.id)
            # Delete shopping cart in database
            current_user.update(old_cart="")

            messages.success(request, "Order Placed!")
            return redirect('home')

        else:
            # not logged in
            # Get the billing form
            billing_form = PaymentForm()

            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_Invoice)
            create_order.save()

            order_id = create_order.pk

            for product in cart_products():
                # get product id
                product_id = product.id
                # Get product price
                if product.best_offer:
                    price = product.sale_price
                else:
                    price = product.price

                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
                        create_order_item.save()

            # Delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    # Delete the key
                    del request.session[key]

            return render(request, "payment/billing_info.html", {"paypal_form": paypal_form, "cart_products": cart_products, "quantities": quantities, "totals": totals, "shipping_info": request.POST, "billing_form": billing_form})

    else:
        messages.success(request, "Access Denied")
        return redirect('home')
            

# def billing_info(request):
#     if request.POST:

#         # Get the cart
#         cart = Cart(request)
#         cart_products = cart.get_prods
#         quantities = cart.get_quants
#         totals = cart.cart_total()

#         # Create a session with shipping info
#         my_shipping = request.POST
#         request.session['my_shipping'] = my_shipping

#         #Get the host
#         host = request.get_host()
#         # Create an Invoice number
#         my_Invoice = str(uuid.uuid4())
    

#         # Create paypal form dictionary
#         paypal_dict = {
#             'business': settings.PAYPAL_RECEIVER_EMAIL,
#             'amount':totals,
#             'item_name': 'ShopNasi orders',
#             'no_shipping': '2',
#             'invoice': my_Invoice,
#             'currency_code': 'USD', 
#             'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
#             'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
#             'cancel_return': 'https://{}{}'.format(host, reverse("payment_failed")),
#         }

#         # Create actual paypal button
#         paypal_form = PayPalPaymentsForm(initial=paypal_dict)



#         # Check to see if user is logged in
#         if request.user.is_authenticated:
#             # Get the billing form 
#             billing_form = PaymentForm()


#             # logged in
#             user = request.user
#             # Create orde
#             create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_Invoice)
#             create_order.save()
            
#             # Add oredr items
#             # Get the order id

#             order_id = create_order.pk

#             # get product info
#             for product in cart_products():
#                 # get product id
#                 product_id = product.id
#                 # Get product price
#                 if product.best_offer:
#                     price = product.sale_price
#                 else:
#                     price = product.price
#                     # Get quantity


#                 for key, value in quantities().items():
#                     if int(key) == product.id:
#                             # create order item
#                         create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
#                         create_order_item.save()


#             # Delete cart fro database(old_cart field)
#             current_user = Profile.objects.filter(user__id=request.user.id)
#             # Delete shopping cart in database
#             current_user.update(old_cart="")


#             messages.success(request, "Order Placed!")
#             return redirect('home')
        
#         else:
#             # not logged in


#             create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_Invoice)
#             create_order.save()

#             order_id = create_order.pk


#             for product in cart_products():
#                 # get product id
#                 product_id = product.id
#                 # Get product price
#                 if product.best_offer:
#                     price = product.sale_price
#                 else:
#                     price = product.price
#                     # Get quantity


#                     for key, value in quantities().items():
#                         if int(key) == product.id:
#                             # create order item
#                             create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
#                             create_order_item.save()

#                 # Delete our cart
#             for key in list(request.session.keys()):
#                 if key == "session_key":
#                     # Delete the key
#                     del request.session[key]







            
#             return render(request,"payment/billing_info.html",{"paypal_form":paypal_form, "cart_products": cart_products,"quantities": quantities,"totals": totals,"shipping_info": request.POST,"billing_form":billing_form})
#         else:
#             # Not logged in
#             # Get the billing form 
#             billing_form = PaymentForm
#             return render(request,"payment/billing_info.html",{"paypal_form":paypal_form, "cart_products": cart_products,"quantities": quantities,"totals": totals,"shipping_info": request.POST,"billing_form":billing_form})

#         # shipping_form = request.POST
#         # return render(request,"payment/billing_info.html",{"cart_products": cart_products,"quantities": quantities,"totals": totals,"shipping_form": shipping_form,})
#     else:
#         messages.success(request, "Access denied!")
#         return redirect('home')
    

def checkout(request):
    # Get the cart
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()


    if request.user.is_authenticated:
        shipping_user, created = ShippingAddress.objects.get_or_create(user=request.user)

        # shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        # Shipping user
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
       # Check out as logged in user
        return render(request,"payment/checkout.html",{"cart_products": cart_products,"quantities": quantities,"totals": totals,"shipping_form": shipping_form,})
    #    Guest

    else:
        shipping_form = ShippingForm(request.POST or None)
        return render(request,"payment/checkout.html",{"cart_products": cart_products,"quantities": quantities,"totals": totals,"shipping_form": shipping_form,})






# Create your views here.
def payment_success(request):
    return render(request, "payment/payment_success.html", {})

def payment_failed(request):
    return render(request, "payment/payment_failed.html", {})
