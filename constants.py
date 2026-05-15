import unicodedata

POSSIBLE_OBJECTS = [
    "Cachorro",
    "Carro",
    "Maca",
    "Bicicleta",
    "Computador",
    "Violao",
    "Livro",
    "Relogio",
    "Aviao",
    "Cadeira",
]

OBJECT_SYNONYMS = {
    "cachorro": ["cao", "dog", "cachorrinho", "cadela"],
    "carro": ["automovel", "veiculo", "caranga", "auto"],
    "maca": ["apple", "fruta"],
    "bicicleta": ["bike", "magrela", "bici"],
    "computador": ["pc", "notebook", "laptop"],
    "violao": ["guitarra", "violaozinho", "viola"],
    "livro": ["obra", "livrinho", "book"],
    "relogio": ["despertador", "watch"],
    "aviao": ["aeronave", "jatinho", "airplane"],
    "cadeira": ["assento", "poltrona", "banco"],
}

MAX_TURNS = 3
SERVER_PORT = 9090
SERVER_HOST = "localhost"


def remove_accents(s):
    return (
        "".join(
            c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
        )
        .lower()
        .strip()
    )
