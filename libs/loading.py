"""
Terminal Loading Indicators and Progress Display Utilities
===========================================================

This module provides utilities for displaying loading indicators and progress bars
in terminal/console applications during long-running operations.
"""

import time
import sys
import ctypes
import threading

# Windows-only imports with fallback
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

class loading:
    def __init__(self, bar_length=10):
        self.bar_length = bar_length
        self._spinner_thread = None
        self._spinner_stop = False

    def display_loading_bar(self, percent, overwrite=True, loading_text="Loading"):
        bar_length = 10  # Length of the loading bar
        filled_length = int(percent * bar_length)
        empty_length = bar_length - filled_length
        
        bar = '[' + '#' * filled_length + '-' * empty_length + ']'
        percent_display = f"{int(percent * 100):2d}%"  # Format the percentage value
        
        loading_bar = f"{loading_text}: {bar} {percent_display}"
        
        if overwrite:
            print(loading_bar, end='\r')
        else:
            print(loading_bar)

    def delay_with_loading_bar(self, seconds, loading_text="Loading"):
        start_time = time.time()  # Get the starting time
        
        while True:
            elapsed_time = time.time() - start_time  # Calculate the elapsed time
            
            if elapsed_time >= seconds:
                break  # Exit the loop if the desired time delay has passed
            
            percent = elapsed_time / seconds
            self.display_loading_bar(percent, overwrite=True, loading_text=loading_text)
            
            time.sleep(0.1)  # Wait for a short period before updating the loading bar

        self.display_loading_bar(1.0, overwrite=True, loading_text=loading_text)

    def delay_with_loading_indicator(self, seconds):
        symbols = ['|', '/', '-', '\\']  # List of loading symbols
        start_time = time.time()  # Get the starting time
        
        while True:
            elapsed_time = time.time() - start_time  # Calculate the elapsed time
            
            if elapsed_time >= seconds:
                break  # Exit the loop if the desired time delay has passed
            
            # Display the loading symbol
            symbol_index = int(time.time()*10) % 4
            sys.stdout.write('\b' + symbols[symbol_index])
            sys.stdout.flush()
            
            time.sleep(0.1)  # Wait for a short period before displaying the next symbol

        sys.stdout.write('\b ')  # Clear the loading symbol
        sys.stdout.flush()

    def input_with_flashing(self, input_prompt=""):
        print(input_prompt)

        if HAS_MSVCRT:
            # Windows-specific flashing behavior
            while True:
                if msvcrt.kbhit():
                    break
                try:
                    ctypes.windll.user32.FlashWindow(ctypes.windll.kernel32.GetConsoleWindow(), True)
                except:
                    pass  # Gracefully handle if windll is not available
                time.sleep(0.5)  # Adjust the delay as needed
            return input()
        else:
            # Non-Windows: simple input without flashing
            return input()

    def _spinner_worker(self, message):
        """Worker thread for the spinner animation."""
        braille_patterns = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        idx = 0
        while not self._spinner_stop:
            sys.stdout.write(f'\r{message} {braille_patterns[idx % len(braille_patterns)]} ')
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(message) + 3) + '\r')
        sys.stdout.flush()

    def start_spinner(self, message="Processing"):
        if self._spinner_thread and self._spinner_thread.is_alive():
            return  # Already running
        
        self._spinner_stop = False
        self._spinner_thread = threading.Thread(target=self._spinner_worker, args=(message,), daemon=True)
        self._spinner_thread.start()

    def stop_spinner(self):
        if self._spinner_thread and self._spinner_thread.is_alive():
            self._spinner_stop = True
            self._spinner_thread.join(timeout=0.5)
            self._spinner_thread = None

    def example_usage(self):
        total_increments = 100
        
        for i in range(total_increments + 1):
            percent = i / total_increments
            self.display_loading_bar(percent, overwrite=True)
            time.sleep(0.1)
        print("\nLoading complete!")

        self.delay_with_loading_indicator(5)
        print("Time delay complete!")