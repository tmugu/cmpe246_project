from mfrc522 import SimpleMFRC522

import time

import RPi.GPIO as GPIO

import tkinter as tk

from tkinter import font

window = tk.Tk()

window.title("RFID CARD READER")

custom_font = font.Font(size=30)

window.geometry("800x400")

RFID_label = tk.Label(window, text="Hold a card near the reader.", anchor='center', font=custom_font)

RFID_label.pack()

CARD_ID_label = tk.Label(window, anchor='center', font=custom_font)

CARD_ID_label.pack()

window.update()

reader = SimpleMFRC522()

def read_rfid():

   

   id, text = reader.read()

   

   if id == None :

       RFID_label.config(fg="red", text="Hold a card near the reader.")

       print("Hold a card near the reader.")

       

     

   else :

       # Scan for cards

       print("CARD DETECTED.")

       RFID_label.config(fg="red", text="CARD DETECTED.")

       # Print the card ID

       print("Card ID:", id)

       CARD_ID_label.config(fg="red", text="Card ID: {} ".format(id))

       window.after(1, read_rfid)

   

GPIO.cleanup()

read_rfid()  

window.mainloop()