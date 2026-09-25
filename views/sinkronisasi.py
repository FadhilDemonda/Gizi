import streamlit as st

def show_sinkronisasi():
    st.header("🔄 Sinkronisasi Data")
    st.write("Tekan tombol di bawah untuk *force sync* (menghapus cache dan memuat ulang data terbaru dari database lokal/CSV).")
    st.write("Digunakan jika Anda mengubah file CSV secara manual dan ingin memperbarui tampilan aplikasi tanpa restart.")
    
    if st.button("🔄 Sync Sekarang (Clear Cache)", type="primary"):
        st.cache_data.clear()
        st.success("Cache berhasil dihapus! Data telah diperbarui dengan yang terbaru.")
        st.rerun()
