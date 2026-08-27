from typing import Dict, Any

def count_entities(data: Dict[str, Any]) -> int:
    """
    Extract the number of entities from a dictionary structure.
    
    Args:
        data: Dictionary containing an "entities" key with a list of entity objects
        
    Returns:
        Number of entities in the entities list
        
    Raises:
        ValueError: If the "entities" key is missing or not a list
    """
    if "entities" not in data:
        raise ValueError("Dictionary must contain an 'entities' key")
    
    if not isinstance(data["entities"], list):
        raise ValueError("'entities' must be a list")
    
    return len(data["entities"])


# # Example usage:
# if __name__ == "__main__":
#     # Your dictionary
#     knowledge_graph = {
#         "entities": [
#             {"id": "algebra", "text": "Algebra", "type": "ScientificConcept"},
#             {"id": "numbers", "text": "Numbers", "type": "ScientificConcept"},
#             # ... more entities
#         ],
#         "relationships": [
#             # ... relationships
#         ],
#         "metadata": {
#             "source_context": "Curriculum extracted from the table of contents",
#             "domain": "Mathematics"
#         }
#     }
    
#     # Count entities
#     entity_count = count_entities(knowledge_graph)
#     print(f"Number of entities: {entity_count}")