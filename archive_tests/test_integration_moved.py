import pytest

@pytest.mark.skip(reason="Integration test spostato in integration_tests/. Esegui il test reale da integration_tests/ o usa -m integration su quella cartella.")
@pytest.mark.integration
def test_real_pipeline_milano():
    pass
