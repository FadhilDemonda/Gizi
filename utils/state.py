import streamlit as st

def init_session_state():
    """
    Initialize all central st.session_state keys used across the app.
    
    Keys documented:
    - tipe_trx (str): Keeps track of the active transaction type button in Transaksi (Masuk or Keluar).
    - form_reset_count (int): Used to uniquely key widgets in Transaksi to force them to clear/reset upon successful submission.
    """
    if 'tipe_trx' not in st.session_state:
        st.session_state.tipe_trx = "+ Stok Masuk"
        
    if 'form_reset_count' not in st.session_state:
        st.session_state.form_reset_count = 0

def set_tipe_trx(tipe: str):
    """
    Callback to update the transaction type in state.
    """
    st.session_state.tipe_trx = tipe
