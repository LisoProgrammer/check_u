---
tags: [checku, dominio, integracion]
---

# RUI — Ventanilla Social del DNP

Registro Único de Identificación del Departamento Nacional de Planeación.
Es contra lo que CheckU valida la identidad.

- Endpoint: `https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI`
- Método: `POST` con `pNumDoc` (el número) y `pTipDoc=3`
- Implementado en `modules/check_id/rui/consultar.py`
- Devuelve `{ok, nombre}` → se normaliza a `{success, message, data:{id, nombre_completo}}`

## Para qué se usa

Se envía el número que se leyó del documento y se compara el nombre que
devuelve contra el nombre que se leyó. Ese cruce es lo que produce el
estado de la solicitud. Ver [[ADR-004 Umbral de similitud 85]].

## Otras fuentes evaluadas

Se identificaron seis fuentes públicas colombianas para validar cédulas:
certificado de vigencia de la RNEC, censo electoral de la RNEC, portal de
antecedentes de la DIJIN, Procuraduría, Contraloría y ADRES/BDUA.

**Ninguna es una API REST documentada**: son formularios web con captcha.
Por eso el RUI —que sí responde a un POST simple— es el único integrado.
Como alternativas comerciales de pago quedaron anotadas Didit y Verifik.

## Nota de entorno

En el entorno de desarrollo en la nube el RUI está bloqueado por el proxy
de salida, así que todas las pruebas locales terminan en `por_revisar`.
La lógica de validación se probó aparte con un RUI simulado — ver
[[Metodología de pruebas]].
