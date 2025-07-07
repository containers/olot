from olot.modelpack import Model


def test_model_deserialization_minimal():
    """Test that Model can deserialize a minimal JSON structure."""
    json_data = {
        "descriptor": {
            "name": "xyz-3-8B-Instruct",
            "version": "3.1"
        },
        "config": {},
        "modelfs": {
            "type": "layers",
            "diffIds": [
                "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            ]
        }
    }
    
    model = Model.model_validate(json_data)
    
    assert model is not None
    assert isinstance(model, Model)
    assert model.descriptor.name == "xyz-3-8B-Instruct"
    assert model.descriptor.version == "3.1"
    assert model.modelfs.type.value == "layers"
    assert len(model.modelfs.diffIds) == 1
    assert model.modelfs.diffIds[0] == "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # test serialization back to JSON
    serialized = model.model_dump_json(exclude_none=True) # to avoid having nulls
    print(serialized)
    assert serialized is not None
    assert isinstance(serialized, str)
    
    # round-trip: verify we can deserialize the serialized data back
    deserialized = Model.model_validate_json(serialized)
    assert deserialized is not None
    assert isinstance(deserialized, Model)
    
    assert deserialized.descriptor.name == model.descriptor.name
    assert deserialized.descriptor.version == model.descriptor.version
    assert deserialized.modelfs.type == model.modelfs.type
    assert deserialized.modelfs.diffIds == model.modelfs.diffIds
