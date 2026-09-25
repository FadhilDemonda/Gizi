def get_header_html(len_items: int) -> str:
    """
    Generate the HTML snippet for the table header in Dashboard.
    
    Args:
        len_items (int): Number of items displayed.
        
    Returns:
        str: HTML string.
    """
    return f"""
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; margin-top: 15px;">
    <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #6b7280;"></div>
    <h3 style="margin: 0; font-size: 1.2rem; color: var(--text-color, #1f2937);">Status Seluruh Inventaris Stok</h3>
    <div style="background-color: rgba(107, 114, 128, 0.1); color: #4b5563; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.9rem;">
        {len_items} Item
    </div>
</div>
    """

def get_row_html(
    nama_barang: str, 
    kode_barang: str, 
    stok: float, 
    satuan: str, 
    minimum: float, 
    bar_width: int, 
    status_text: str, 
    color_hex: str, 
    bg_color: str, 
    text_color: str, 
    icon: str, 
    estimasi: str
) -> tuple[str, str, str]:
    """
    Generate HTML snippets for the three columns of a dashboard item row.
    
    Returns:
        tuple[str, str, str]: (col1_html, col2_html, col3_html)
    """
    c1 = f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
        <div style="font-size: 1.5rem; background-color: {bg_color}; color: {color_hex}; border-radius: 8px; min-width: 45px; height: 45px; display: flex; align-items: center; justify-content: center;">{icon}</div>
        <div>
            <div style="font-weight: 600; font-size: 1rem;">{nama_barang}</div>
            <div style="font-size: 0.85rem; color: gray;">{kode_barang}</div>
        </div>
    </div>
    """
    
    c2 = f"""
    <div style="margin-bottom: 10px;">
        <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-size: 1.25rem; font-weight: 700; color: {color_hex};">{stok}</span>
            <span style="font-size: 0.9rem; font-weight: 600; color: {color_hex};">{satuan}</span>
            <span style="font-size: 0.8rem; color: gray; margin-left: 8px;">Min: {minimum} {satuan}</span>
        </div>
        <div style="width: 80%; height: 6px; background-color: rgba(128,128,128,0.2); border-radius: 4px; overflow: hidden; margin-top: 4px;">
            <div style="height: 100%; width: {bar_width}%; background-color: {color_hex};"></div>
        </div>
        <div style="font-size: 0.75rem; color: gray; margin-top: 2px;">Kapasitas Max: {max(1.0, minimum * 2)}</div>
    </div>
    """
    
    c3 = f"""
    <div style="margin-bottom: 10px; display: flex; flex-direction: column; gap: 4px;">
        <div style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; background-color: {bg_color}; color: {text_color}; border: 1px solid {color_hex}40; width: fit-content;">
            {status_text}
        </div>
        <div style="font-size: 0.8rem; color: gray;">⏱️ {estimasi}</div>
    </div>
    """
    return c1, c2, c3
