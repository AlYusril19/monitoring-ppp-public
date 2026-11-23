def format_rupiah(amount):
    """Format angka menjadi 'Rp1.234'."""
    return f"Rp{amount:,.0f}".replace(',', '.')