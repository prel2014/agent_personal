import matplotlib.pyplot as plt
import numpy as np

plt.style.use("upao.mplstyle")


def fun(data: dict, titulo: str):
    categorias = data["categorias"]
    subgrupos = data["subgrupos"]
    matriz = data["matriz"]

    x = np.arange(len(categorias))
    n = len(subgrupos)

    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    for i in range(n):
        desplazamiento = (i - (n - 1) / 2) * width

        ax.bar(
            x + desplazamiento,
            matriz[:, i],
            width,
            label=subgrupos[i]
        )

    ax.set_title(titulo)
    ax.set_xlabel("Carreras profesionales")
    ax.set_ylabel("Cantidad de alumnos")

    ax.set_xticks(x)
    ax.set_xticklabels(categorias, rotation=35, ha="right")

    ax.legend()
    plt.tight_layout()
    plt.show()


data = {
    "categorias": [
        "Ingeniería de Software",
        "Arquitectura",
        "Medicina",
        "Derecho",
        "Administración",
        "Psicología"
    ],
    "subgrupos": ["Masculino", "Femenino"],
    "matriz": np.array([
        [320, 180],
        [210, 260],
        [280, 340],
        [190, 310],
        [230, 290],
        [120, 380]
    ])
}


fun(data, "Cantidad de alumnos por carrera y sexo")