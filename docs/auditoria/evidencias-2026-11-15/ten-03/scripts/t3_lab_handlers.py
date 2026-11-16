"""SIMULAÇÃO DE LABORATÓRIO (não é proposta de código): padroniza status e corpo de TODO erro 400 de validação."""
from rest_framework.views import exception_handler


def handler_generico(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code == 400:
        response.data = {'detail': 'Não foi possível concluir a operação com os dados informados.'}
    return response
