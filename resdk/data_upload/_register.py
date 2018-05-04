"""Patch ReSDK Resolwe objects with import methods."""

from resdk.data_upload.annotate_samples import annotate_samples, export_annotation
from resdk.resources import Collection

Collection.annotate = annotate_samples
Collection.export_annotation = export_annotation
