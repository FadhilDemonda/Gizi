import streamlit as st

def inject_custom_css():
    """
    Inject global custom CSS for the application (fonts, buttons, etc).
    """
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

def inject_transaction_button_css(active_type: str):
    """
    Inject dynamic CSS for transaction buttons based on active type.
    """
    if active_type == '+ Stok Masuk':
        primary_color = "#0f9d58" # Green
        hover_color = "#0b7340"
    else:
        primary_color = "#d32f2f" # Red
        hover_color = "#9a0007"
        
    st.markdown(f"""
        <style>
            button[kind="primary"], button[data-testid="baseButton-primary"] {{
                background-color: {primary_color} !important;
                border-color: {primary_color} !important;
            }}
            button[kind="primary"]:hover, button[data-testid="baseButton-primary"]:hover {{
                background-color: {hover_color} !important;
                border-color: {hover_color} !important;
                color: white !important;
            }}
        </style>
    """, unsafe_allow_html=True)
