from __future__ import annotations


def mascarar_cpf(cpf: str) -> str:
    """`12345678901` -> `123.***.***-01`.

    Decisão 8: o CPF fica em texto puro no banco (criptografar quebraria a unique
    constraint e a busca), e a proteção vem do mascaramento na exibição. Mostra o
    bastante para o operador reconhecer a pessoa numa lista, sem expor o documento.
    """
    if len(cpf) != 11 or not cpf.isdigit():
        return cpf
    return f"{cpf[:3]}.***.***-{cpf[9:]}"
