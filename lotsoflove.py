import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import tkinter as tk
from tkinter import messagebox
from firebase_admin import credentials, firestore, initialize_app
import threading
import time
import os
import sys
from stepper_contro4l import rotate_motors_for_selected_items
# Firebase Initialization
cred = credentials.Certificate("/home/SEVENTH/myenv/vendorforyou-62be1-firebase-adminsdk-leiv4-73faaab314.json")
initialize_app(cred)
db = firestore.client()

# RFID Reader Initialization
reader = SimpleMFRC522()
GPIO.setwarnings(False)

# Prices of items
ITEM_PRICES = {
    "Bathing Soap": 20,
    "Toothpaste": 20,
    "Detergent": 10,
    "Sanitary Pad": 5
}

# Function to fetch item details from Firestore
def fetch_item_details():
    try:
        items_ref = db.collection('items')
        items = {}
        for doc in items_ref.stream():
            item_data = doc.to_dict()
            items[item_data['name']] = {
                'price': item_data['price'],
                'quantity': item_data['quantity']
            }
        return items
    except Exception as e:
        print(f"Error fetching items: {e}")
        return {}

# Function to update item quantity in Firestore
def update_item_quantity(item_name, quantity_change):
    try:
        items_ref = db.collection('items')
        query = items_ref.where('name', '==', item_name).stream()
        for item in query:
            current_quantity = item.to_dict()['quantity']
            new_quantity = current_quantity + quantity_change
            item.reference.update({'quantity': new_quantity})
    except Exception as e:
        print(f"Error updating quantity for {item_name}: {e}")

# Function to check user by UID
def check_user_by_uid(uid):
    try:
        uid_str = str(uid)
        query = db.collection('users').where('uid', '==', uid_str).stream()
        for user in query:
            user_data = user.to_dict()
            if user_data.get('approved', False):
                return user_data['name'], user.id, user_data['balance']
        return None, None, None
    except Exception as e:
        print(f"Error checking user: {e}")
        return None, None, None

# Function to get previous booking details for the user
def get_previous_booking(user_email):
    try:
        bookings_ref = db.collection('bookings')
        query = bookings_ref.where('userEmail', '==', user_email).limit(1).stream()

        for booking in query:
            return booking.to_dict()

        return None
    except Exception as e:
        print(f"Error fetching booking details: {e}")
        return None

# Function to delete the booking from Firestore
def delete_booking(user_email):
    try:
        bookings_ref = db.collection('bookings').where('userEmail', '==', user_email).stream()
        for booking in bookings_ref:
            booking.reference.delete()  # Delete the booking
        print("Booking successfully deleted.")
    except Exception as e:
        print(f"Error deleting booking: {e}")

# Function to scan RFID card and check user details
def scan_rfid():
    try:
        status_label.config(text="Scanning for RFID card...", bg='#4CAF50', fg='white')
        root.update()

        uid, _ = reader.read()
        user_name, user_email, user_balance = check_user_by_uid(uid)

        if user_name:
            status_label.config(text=f"Welcome, {user_name}!", bg='#4CAF50', fg='white')

            # Get previous booking if exists
            previous_booking = get_previous_booking(user_email)
            if previous_booking:
                show_previous_booking_page(previous_booking)
            else:
                show_selection_page(user_name, user_email, user_balance)
        else:
            status_label.config(text="Access Denied", bg='#FF5722', fg='white')
    except Exception as e:
        print(f"Error scanning RFID: {e}")
  #   finally:
   #      GPIO.cleanup()

# Function to ********************************************************************************************************************************************************************************************************************show previous booking details if it exists
def show_previous_booking_page(previous_booking):
    def proceed_to_payment():
        total_price = previous_booking['totalPrice']
        if total_price > 0:
            # Proceed with payment logic
            status_label.config(text="Scan RFID to confirm payment.", bg='#4CAF50', fg='white')
            root.update()

            uid, _ = reader.read()
            _, email, balance = check_user_by_uid(uid)

            if email == previous_booking['userEmail']:
                new_balance = balance - total_price
                db.collection('users').document(previous_booking['userEmail']).update({'balance': new_balance})

                # Deduct item quantities from Firestore
                selected_items = previous_booking['selectedItems']
                #for item, count in selected_items.items():
                #    update_item_quantity(item, -selected_items[item]['count'])
                rotate_motors_for_selected_items(selected_items)

                # Delete booking after payment
                delete_booking(previous_booking['userEmail'])

                # Clear the current frame
                for widget in root.winfo_children():
                    widget.destroy()

                # Display remaining balance
                tk.Label(root, text=f"Payment successful!\nRemaining balance: Rs {new_balance}", font=("Arial", 14), bg='#4CAF50', fg='white').pack(pady=20)

                # Exit button to restart the program
                tk.Button(root, text="Exit", command=exit_to_scan, bg='#FFC107', fg='black', font=("Arial", 12)).pack(pady=10)

            else:
                messagebox.showerror("Payment Error", "RFID does not match.")
        else:
            messagebox.showerror("Payment Error", "No items selected.")

    def cancel_booking():
        try:
            # Add back the item quantities to Firestore before deleting the booking
            selected_items = previous_booking['selectedItems']
            for item, count in selected_items.items():
                update_item_quantity(item, count)  # Add the quantity back

            # Delete the booking from Firestore
            delete_booking(previous_booking['userEmail'])
            status_label.config(text="Booking cancelled.", bg='#FF5722', fg='white')
            previous_booking_frame.destroy()
        except Exception as e:
            messagebox.showerror("Cancellation Error", f"Failed to cancel booking: {e}")

    # Show booking details
       # Create frame for previous booking details
    previous_booking_frame = tk.Frame(root, bg='#F5F5F5')
    previous_booking_frame.pack(pady=20, padx=20, fill="both", expand=True)

    tk.Label(previous_booking_frame, text="Previous Booking:", bg='#F5F5F5', font=("Arial", 14)).pack(pady=5)
    tk.Label(previous_booking_frame, text=f"Total Price: Rs {previous_booking['totalPrice']}", bg='#F5F5F5').pack(pady=5)

    for item, count in previous_booking['selectedItems'].items():
        tk.Label(previous_booking_frame, text=f"{item}: {count}", bg='#F5F5F5').pack(pady=2)

    # Create a button frame to align buttons properly
    button_frame = tk.Frame(previous_booking_frame, bg='#F5F5F5')
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Proceed to Payment", command=proceed_to_payment, bg='#4CAF50', fg='white', font=("Arial", 12)).grid(row=0, column=0, padx=5, pady=5)
    tk.Button(button_frame, text="Cancel Booking", command=cancel_booking, bg='#FF5722', fg='white', font=("Arial", 12)).grid(row=0, column=1, padx=5, pady=5)
    tk.Button(button_frame, text="Exit", command=exit_to_scan, bg='#FFC107', fg='black', font=("Arial", 12)).grid(row=0, column=2, padx=5, pady=5)


# Function to show item selection page
def show_selection_page(user_name, user_email, user_balance):
    items = fetch_item_details()

    def update_item_count(item, count):
       if count > 0 and selected_items[item]['quantity'] < 1:
           messagebox.showerror("Out of Stock", f"{item} is out of stock.")
           return

       if selected_items[item]['count'] + count < 0:
           messagebox.showerror("Selection Error", "Cannot deselect below 0.")
           return

       if selected_items[item]['count'] + count <= 3 and sum(i['count'] for i in selected_items.values()) + count <= 9:
           selected_items[item]['count'] += count
           selected_items[item]['quantity'] -= count  # Correct adjustment for both selecting and deselecting

           item_labels[item].config(
               text=f"{item} ({selected_items[item]['count']} selected) - {selected_items[item]['quantity']} available"
        )
           total_price = sum(i['count'] * i['price'] for i in selected_items.values())
           total_price_label.config(text=f"Total: Rs {total_price}")
       else:
           messagebox.showerror("Selection Error", "Cannot select more than 3 per item or 9 total.")

    def proceed_to_payment():
        total_price = sum(i['count'] * i['price'] for i in selected_items.values())

        if total_price > 0 and user_balance >= total_price:
            status_label.config(text="Scan RFID to confirm payment.", bg='#4CAF50', fg='white')
            root.update()

            uid, _ = reader.read()
            _, email, balance = check_user_by_uid(uid)

            if email == user_email:
                # Deduct balance and update Firestore
                new_balance = balance - total_price
                db.collection('users').document(user_email).update({'balance': new_balance})

                # Deduct item quantities from Firestore
                for item, data in selected_items.items():
                  #  update_item_quantity(item, -selected_items[item]['count'])
                    update_item_quantity(item, -data['count'])
                    # After updating balance and quantities
              #   print(selected_items)
                rotate_motors_for_selected_items(selected_items)
                


                # Delete the booking (if exists)
             #    delete_booking(user_email)

                # Clear the selection page
                for widget in root.winfo_children():
                    widget.destroy()

                # Show remaining balance and exit button
                payment_success_frame = tk.Frame(root)
                payment_success_frame.pack(pady=20)

                tk.Label(payment_success_frame, text=f"Payment successful!\nRemaining balance: Rs {new_balance}", 
                         font=("Arial", 14), bg='#4CAF50', fg='white').pack(pady=10)

                tk.Button(payment_success_frame, text="Exit", command=exit_to_scan, 
                          bg='#FFC107', fg='black', font=("Arial", 12)).pack(pady=10)

            else:
                messagebox.showerror("Payment Error", "RFID does not match.")
        elif total_price == 0:
            messagebox.showerror("Payment Error", "No items selected.")
        else:
            messagebox.showerror("Payment Error", "Insufficient balance.")

    selected_items = {
        item: {'count': 0, 'price': data['price'], 'quantity': data['quantity']}
        for item, data in items.items()
    }
    item_labels = {}

    selection_frame = tk.Frame(root)
    selection_frame.pack()

    tk.Label(
        selection_frame, text=f"Hello, {user_name}! Remaining balance: Rs {user_balance}"
    ).pack(pady=5)

    for item, data in selected_items.items():
        frame = tk.Frame(selection_frame)
        frame.pack(pady=2)

        label_text = f"{item} ({selected_items[item]['count']} selected) - {selected_items[item]['quantity']} available"
        item_labels[item] = tk.Label(frame, text=label_text)
        item_labels[item].pack(side=tk.LEFT)

        tk.Button(frame, text="+", command=lambda i=item: update_item_count(i, 1)).pack(side=tk.LEFT)
        tk.Button(frame, text="-", command=lambda i=item: update_item_count(i, -1)).pack(side=tk.LEFT)

    total_price_label = tk.Label(selection_frame, text="Total: Rs 0")
    total_price_label.pack(pady=5)

    tk.Button(selection_frame, text="Proceed to Payment", command=proceed_to_payment).pack()
    tk.Button(selection_frame, text="Exit", command=exit_to_scan, bg='#FFC107', fg='black', font=("Arial", 12)).pack(pady=5)

    

def exit_to_scan():
    GPIO.cleanup()  # Clears GPIO pins
    root.destroy()  # Close the current application window
    os.execv(sys.executable, ['python3'] + sys.argv)  # Restart the script



# Main Application
root = tk.Tk()
root.title("Vending Machine")
root.geometry("800x480")
root.configure(bg='#F5F5F5')

# Add a label to display scanning status
status_label = tk.Label(root, text="Please scan your RFID card", font=("Arial", 14), bg='#4CAF50', fg='white')
status_label.pack(pady=20)

# Add a Scan RFID button
scan_rfid_button = tk.Button(root, text="Scan RFID", command=scan_rfid, bg='#4CAF50', fg='white', font=("Arial", 12))
scan_rfid_button.pack(pady=10)

root.mainloop()



