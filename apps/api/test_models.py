from services.ai import list_available_models

models = list_available_models()

for model in models.data:
    print(model.id)