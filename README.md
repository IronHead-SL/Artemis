# <img src="artemis-logo.png" width="40" height="40" /> Artemis

Artemis es una plataforma diseñada para la exploración y descubrimiento de patrimonio cultural del Met Museum. El sistema combina técnicas de **Visión Artificial (Deep Learning)** con **Bases de Datos de Grafos** para ofrecer una experiencia de búsqueda híbrida, permitiendo identificar obras mediante imágenes y navegar por sus conexiones históricas y semánticas.


## Arquitectura
El proyecto ha sido desarrollado siguiendo una **Arquitectura Hexagonal (Puertos y Adaptadores)**. Esta estructura desacopla la lógica de negocio de los servicios externos (APIs del MET, Wikipedia, Wikidata), garantizando un sistema modular, escalable y mantenible.

### Tecnologías empleadas:
* **Orquestación:** Docker & Docker Compose.
* **Persistencia:** MongoDB (almacenamiento documental) y Neo4j (grafo de relaciones).
* **Ingesta:** Pipelines paralelos con control de flujo adaptativo.
* **IA (En desarrollo):** Integración con PyTorch para la generación de *embeddings* visuales.


## 🚀 Cómo ejecutar el proyecto

Para levantar el entorno completo, asegúrate de tener instalado **Docker** y **Docker Compose**.

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/IronHead-SL/Artemis
   ```

2. **Levantar los servicios:**
   ```bash
   docker-compose up -d
   ```

## Estado de la Entrega (Intermedia)

Esta entrega corresponde al **hito de infraestructura e ingesta de datos**. En esta fase se han completado los siguientes objetivos:

* Pipeline de extracción y limpieza de datos (MET, Wikidata, Wikipedia).
* Implementación de arquitectura hexagonal y orquestación con Docker.
* Persistencia híbrida configurada (MongoDB + Neo4j).
* Control de flujo implementado para el cumplimiento de límites de APIs externas.

*Pendiente:* Módulo de IA (PyTorch), indexación en Qdrant e interfaz Streamlit (en desarrollo).

*Desarrollado por: Pablo Herrera Gonzalez y Pablo Cabeza Lantigua*
