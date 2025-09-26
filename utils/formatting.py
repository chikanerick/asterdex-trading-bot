from decimal import Decimal, ROUND_DOWN

def floor_to_step(q: Decimal, step: Decimal) -> Decimal:
    steps = (q / step).to_integral_value(rounding=ROUND_DOWN)
    return steps * step

def format_float2(x: Decimal, precision: int) -> str:
    quantized = x.quantize(Decimal(f"1e-{precision}"), rounding=ROUND_DOWN)
    return format(quantized, f".{precision}f")

def format_float(x: Decimal) -> str:
    s = format(x, 'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s