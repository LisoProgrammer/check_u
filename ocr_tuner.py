import streamlit as st
import cv2
import numpy as np
from PIL import Image
from io import BytesIO


st.title("OCR Image Tuner")


uploaded = st.file_uploader(
    "Sube una imagen",
    type=["png", "jpg", "jpeg"]
)


if uploaded:

    img = Image.open(uploaded)

    img = np.array(img)

    if len(img.shape) == 3:
        gray = cv2.cvtColor(
            img,
            cv2.COLOR_RGB2GRAY
        )
    else:
        gray = img


    h = st.slider(
        "Denoising h",
        0,
        30,
        10
    )


    blur = st.slider(
        "Gaussian Blur",
        1,
        15,
        3,
        step=2
    )


    block = st.slider(
        "Adaptive block size",
        3,
        51,
        21,
        step=2
    )


    c = st.slider(
        "Threshold C",
        0,
        20,
        5
    )


    zoom = st.slider(
        "Zoom",
        1,
        5,
        2
    )


    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=h,
        templateWindowSize=7,
        searchWindowSize=21
    )


    blurred = cv2.GaussianBlur(
        denoised,
        (blur, blur),
        0
    )


    result = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block,
        c
    )


    # aplicar zoom solo para visualización
    height, width = gray.shape

    gray_zoom = cv2.resize(
        gray,
        (width * zoom, height * zoom),
        interpolation=cv2.INTER_NEAREST
    )

    result_zoom = cv2.resize(
        result,
        (width * zoom, height * zoom),
        interpolation=cv2.INTER_NEAREST
    )


    st.subheader("Original")

    st.image(
        gray_zoom,
        use_container_width=True
    )


    st.subheader("Procesada")

    st.image(
        result_zoom,
        use_container_width=True
    )


    # descarga de imagen procesada
    buffer = BytesIO()

    Image.fromarray(result).save(
        buffer,
        format="PNG"
    )


    st.download_button(
        label="Descargar imagen procesada",
        data=buffer.getvalue(),
        file_name="procesada.png",
        mime="image/png"
    )