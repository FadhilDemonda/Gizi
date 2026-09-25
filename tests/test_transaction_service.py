from services.transaction_service import validate_stock_out, compute_stok_akhir, generate_transaction_id

def test_validate_stock_out():
    valid, final = validate_stock_out(10, 5)
    assert valid is True
    assert final == 5
    
    valid, final = validate_stock_out(10, 15)
    assert valid is False
    assert final == -5

def test_compute_stok_akhir():
    assert compute_stok_akhir(10, 5, 'Masuk') == 15
    assert compute_stok_akhir(10, 5, 'Keluar') == 5
    assert compute_stok_akhir(10, 5, 'Edit') == 10

def test_generate_transaction_id():
    assert generate_transaction_id(0) == "T0001"
    assert generate_transaction_id(99) == "T0100"
