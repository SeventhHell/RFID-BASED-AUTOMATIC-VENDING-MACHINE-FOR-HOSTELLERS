import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# Define GPIO pins for the stepper motors
motor_pins = {
    'Toothpaste'  : {'en': 5, 'dir': 6, 'step': 13},
    'Detergent' :{ 'en': 23, 'dir': 24, 'step':18},
    'Bathing Soap' : { 'en': 22, 'dir': 27, 'step': 17},
    'Sanitary Pad': {'en': 1, 'dir':12, 'step':26 }
}

# Initialize motor pins
for motor, pins in motor_pins.items():
    GPIO.setup(pins['en'], GPIO.OUT)
    GPIO.setup(pins['dir'], GPIO.OUT)
    GPIO.setup(pins['step'], GPIO.OUT)
    GPIO.output(pins['en'], GPIO.LOW)  # Enable motor

# Define the steps per item (adjust based on your setup)
STEPS_PER_ITEM = 200  # For NEMA 17 with 1.8° per step, this is for a full revolution.

def rotate_stepper(motor_name, rotations, direction=GPIO.HIGH, rotation_delay=0.5):
    """Rotate a stepper motor by a specific number of full rotations with a delay between rotations."""
    try:
        if motor_name not in motor_pins:
            print(f"Error: {motor_name} motor is not defined.")
            return

        pins = motor_pins[motor_name]
        GPIO.output(pins['dir'], direction)  # Set direction

        # Perform the specified number of rotations
        for _ in range(rotations):
            for _ in range(STEPS_PER_ITEM):  # Complete one full rotation
                GPIO.output(pins['step'], GPIO.HIGH)
                time.sleep(0.009)  # Adjust for motor speed
                GPIO.output(pins['step'], GPIO.LOW)
                time.sleep(0.009)  # Adjust for motor speed
            
            # Introduce a delay between full rotations
            time.sleep(rotation_delay)

        print(f"{motor_name} motor rotated {rotations} full rotations in direction {'CW' if direction == GPIO.HIGH else 'CCW'}.")

    except Exception as e:
        print(f"Error rotating motor {motor_name}: {e}")

def rotate_motors_for_selected_items(selected_items):
    """Rotate motors for selected items based on their count."""
    try:
        for item, data in selected_items.items():
            # Determine the count based on the type of data
            if isinstance(data, dict):  # If data is a dictionary, extract 'count'
                count = data.get('count', 0)
            elif isinstance(data, int):  # If data is an integer, treat it as count
                count = data
            else:
                print(f"Skipping {item}: Invalid data type ({type(data)}).")
                continue  # Skip invalid data types

            # Proceed if count is greater than 0
            if count > 0:
                rotate_stepper(item, count, direction=GPIO.HIGH, rotation_delay=0.5)
                print(f"{item}: Rotated {count} full rotations.")
            else:
                print(f"Skipping {item}: No rotations needed (count = {count}).")
    except Exception as e:
        print(f"Error in rotating motors: {e}")
    finally:
        GPIO.cleanup()  # Reset GPIO pins after operation

# Example usage
if __name__ == "__main__":
    selected_items = {
        'Bathing Soap': 2,  # 2 full rotations needed
        'Toothpaste': 3,    # 1 full rotation needed
        'Detergent': 2,
        'Sanitary Pad' : 3,
    }
    rotate_motors_for_selected_items(selected_items)
    