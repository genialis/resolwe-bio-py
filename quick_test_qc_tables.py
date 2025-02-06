import resdk
from resdk.tables import QCTables

app = resdk.Resolwe(url="https://app.genialis.com")
app.login()

c = app.collection.get("qctables-test-collection")

qt = QCTables(c)
qt.clear_cache()
qt = QCTables(c)

# ----
print("=" * 100)
print(qt.general)
print(qt.macs)
print(qt.chipseq_postpeak)
print(qt.chipseq_prepeak)
print(qt.picard_alignment_summary)
print(qt.picard_wgs_metrics)
print(qt.picard_insert_size_metrics)
print(qt.picard_duplication_metrics)
print(qt.qc)
