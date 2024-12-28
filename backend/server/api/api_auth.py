from flask import Blueprint, request


auth: Blueprint = Blueprint(
    name='api_auth',
    import_name=__name__,
)

@auth.route('/')
def _():
    ...
