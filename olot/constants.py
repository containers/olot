# Layer annotation keys for content metadata
ANNOTATION_LAYER_CONTENT_DIGEST = "olot.layer.content.digest"  # digest/hash of the original file; not the tar digest, not the targz digest (layer digest). Not available for files
ANNOTATION_LAYER_CONTENT_TYPE = "olot.layer.content.type"  # either file or directory
ANNOTATION_LAYER_CONTENT_INLAYERPATH = "olot.layer.content.inlayerpath"  # the content of the tar/targz location as expanded on the container FS
ANNOTATION_LAYER_CONTENT_NAME = "olot.layer.content.name"  # the original path.name
