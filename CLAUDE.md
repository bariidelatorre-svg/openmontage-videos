# Reglas de trabajo (generación de imágenes Higgsfield)

- API: `higgsfield-client` (pip) con la variable `HF_KEY`. No usar el conector MCP para generar (solo para consultar saldo/modelos).
- Modelo por defecto: **Nano Banana Pro** (`nano_banana_pro`, 2k), siempre con las imágenes de `clientes/<clienta>/referencias/` como `image_references`.
- Cada clienta tiene su carpeta en `clientes/`. Usar sus referencias directamente: **no pedir las imágenes otra vez**.
- **Nunca generar nada desde cero** (sin referencias o con un concepto nuevo) sin consultar antes.
- Formato por defecto: **4:5**. Al entregar una imagen 4:5, preguntar si también se necesita en **9:16**.
- Después de cada generación, informar los **créditos restantes**.
- Si algo falla, intentar arreglarlo primero (parámetros, prompt, código) **sin gastar créditos extra**; no reintentar generaciones a ciegas.
- Respuestas breves y rápidas: mostrar solo el resultado, sin narrar el proceso interno.
- Guardar resultados en `clientes/<clienta>/salidas/`.
