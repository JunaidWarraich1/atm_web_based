import hashlib
import time

class TerminalColor:
    """ANSI color codes for rendering premium console UI."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def color_text(text: str, color_code: str) -> str:
    """Wraps text with ANSI color codes."""
    return f"{color_code}{text}{TerminalColor.END}"


def hash_pin(pin: str) -> str:
    """Secures a PIN using SHA-256 hashing."""
    return hashlib.sha256(pin.encode('utf-8')).hexdigest()


def validate_pin_format(pin: str) -> bool:
    """
    Enforces security rules for a new PIN.
    Rules:
    - Must be exactly 4 digits.
    - Cannot be a simple sequence (e.g., '1234', '4321', '0000', '1111').
    """
    if not (pin.isdigit() and len(pin) == 4):
        return False
    
    # Check for identical digits (e.g., '1111')
    if len(set(pin)) == 1:
        return False
        
    # Check sequential digits
    sequential_ups = "0123456789"
    sequential_downs = "9876543210"
    if pin in sequential_ups or pin in sequential_downs:
        return False
        
    return True


def render_table(headers: list, rows: list) -> str:
    """
    Renders data in a neatly formatted ASCII table for the console.
    """
    if not headers:
        return ""
        
    # Compute column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))
            
    # Form layout
    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_str = "| " + " | ".join(f"{h:<{col_widths[idx]}}" for idx, h in enumerate(headers)) + " |"
    
    lines = [sep, header_str, sep]
    for row in rows:
        row_str = "| " + " | ".join(f"{str(val):<{col_widths[idx]}}" for idx, val in enumerate(row)) + " |"
        lines.append(row_str)
    lines.append(sep)
    
    return "\n".join(lines)


def print_simulated_loading(action_name: str, duration: float = 1.0):
    """Simulates realistic delay to mimic hardware connection or processing time."""
    steps = 4
    step_duration = duration / steps
    print(color_text(f"{action_name}...", TerminalColor.CYAN), end="", flush=True)
    for _ in range(steps):
        time.sleep(step_duration)
        print(".", end="", flush=True)
    print(" Done!")
