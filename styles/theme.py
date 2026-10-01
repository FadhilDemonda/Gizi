import streamlit as st

def inject_custom_css():
    """
    Inject global custom CSS for the application (fonts, buttons, etc).
    """
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        /* Global Typography */
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        
        /* Soft subtle animation for everything */
        * {
            transition: background-color 0.1s, border-color 0.1s;
        }

        /* Modern Container / Card Styling for bordered containers */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.03) !important;
            background-color: var(--secondary-background-color);
            transition: all 0.3s ease;
            overflow: hidden;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.06) !important;
        }

        /* Modern Button Styling */
        button[kind="secondary"] {
            border-radius: 8px !important;
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        button[kind="secondary"]:hover {
            border-color: rgba(128, 128, 128, 0.4) !important;
            background: rgba(128, 128, 128, 0.05) !important;
            transform: translateY(-1px);
        }
        
        /* Primary button default transition */
        button[kind="primary"] {
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
            transition: all 0.2s ease !important;
        }
        button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.15) !important;
        }

        /* Tombol Bersihkan Semua (Yellow Accent) */
        div[data-testid="column"]:has(.btn-clear-target, #btn-bersihkan) button,
        div[data-testid="stElementContainer"]:has(.btn-clear-target, #btn-bersihkan) + div[data-testid="stElementContainer"] button {
            background-color: #facc15 !important;
            color: #000000 !important;
            border: 1px solid #eab308 !important;
            font-weight: 700 !important;
        }
        div[data-testid="column"]:has(.btn-clear-target, #btn-bersihkan) button p,
        div[data-testid="column"]:has(.btn-clear-target, #btn-bersihkan) button span,
        div[data-testid="stElementContainer"]:has(.btn-clear-target, #btn-bersihkan) + div[data-testid="stElementContainer"] button p,
        div[data-testid="stElementContainer"]:has(.btn-clear-target, #btn-bersihkan) + div[data-testid="stElementContainer"] button span {
            color: #000000 !important;
            font-weight: 700 !important;
        }
        div[data-testid="column"]:has(.btn-clear-target, #btn-bersihkan) button:hover,
        div[data-testid="stElementContainer"]:has(.btn-clear-target, #btn-bersihkan) + div[data-testid="stElementContainer"] button:hover {
            background-color: #eab308 !important;
            border-color: #ca8a04 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(234, 179, 8, 0.35) !important;
        }
        /* Sembunyikan elemen penanda agar tidak memakan ruang layout */
        div[data-testid="stElementContainer"]:has(.btn-clear-target, #btn-bersihkan) {
            display: none !important;
            margin: 0 !important;
            padding: 0 !important;
            height: 0 !important;
        }

        /* Input Fields Styling */
        div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"] {
            border-radius: 8px !important;
        }

        /* Metric Styling (make it look premium) */
        div[data-testid="stMetricValue"] {
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            color: var(--text-color) !important;
            font-size: 2.2rem !important;
        }
        div[data-testid="stMetricLabel"] {
            font-weight: 600 !important;
            color: gray !important;
            text-transform: uppercase;
            font-size: 0.8rem !important;
            letter-spacing: 0.5px;
        }

        /* Tab styling */
        button[data-baseweb="tab"] {
            font-weight: 600 !important;
            font-size: 1rem !important;
        }
        
        /* Adjust spacing for horizontal rules */
        hr {
            margin-top: 2em;
            margin-bottom: 2em;
            opacity: 0.5;
        }
        
        /* Dialog Popups */
        div[data-testid="stModal"] div[role="dialog"] {
            border-radius: 16px !important;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2) !important;
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
