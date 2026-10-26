import copy
import uuid
from PIL import ImageDraw, ImageFont


import io
import os

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ExifTags
from pillow_heif import register_heif_opener

# =========================================================
# CONFIGURATION
# =========================================================
register_heif_opener()

st.set_page_config(
    page_title="Pixel Studio | Image Editor",
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# RESET FUNCTION
# Streamlit executes button callbacks before rerunning the app.
# This allows widget values to be safely reset.
# =========================================================
EDITOR_KEYS = [
    "rotation",
    "custom_rotation_enabled",
    "custom_rotation",
    "scale",
    "custom_scale_enabled",
    "custom_scale",
    "brightness",
    "contrast",
    "saturation",
    "sharpness",
    "blur_enabled",
    "blur_radius",
    "edge_enabled",
    "invert_enabled",
    "grayscale_enabled",
    "posterize_enabled",
    "posterize_bits",
    "solarize_enabled",
    "solarize_threshold",
    "output_format",
    "export_quality",
    "export_bytes",
    "export_format",
    "export_signature",
]



def reset_editor():
    """Restore all editor controls to their default values."""

    defaults = {
        "rotation": 0,
        "custom_rotation_enabled": False,
        "custom_rotation": 0,
        "scale": 100,
        "custom_scale_enabled": False,
        "custom_scale": 100,
        "brightness": 1.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "sharpness": 1.0,
        "blur_enabled": False,
        "blur_radius": 2.0,
        "edge_enabled": False,
        "invert_enabled": False,
        "grayscale_enabled": False,
        "posterize_enabled": False,
        "posterize_bits": 4,
        "solarize_enabled": False,
        "solarize_threshold": 128,
        "output_format": "PNG",
        "export_quality": 95,
    }

    # Restore each widget to its default value.
    for key, value in defaults.items():
        st.session_state[key] = value

    # Clear any previously prepared export.
    st.session_state["export_bytes"] = None
    st.session_state["export_format"] = None
    st.session_state["export_signature"] = None


    for key, value in defaults.items():
        st.session_state[key] = value

# =========================================================
# SHADCN-INSPIRED DARK THEME
# =========================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #09090b;
        --surface: #111113;
        --surface-hover: #18181b;
        --border: #27272a;
        --text: #fafafa;
        --muted: #a1a1aa;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(9,9,11,.9);
        border-bottom: 1px solid var(--border);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1500px;
        padding: 2rem 2.2rem 3rem;
    }

    [data-testid="stSidebar"] {
        background: #0c0c0e;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem;
    }

    h1, h2, h3 {
        color: var(--text);
        letter-spacing: -0.04em;
    }

    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    h2 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }

    h3 {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }

    p, label, .stCaption {
        color: var(--muted);
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: .95rem !important;
        margin-top: 1.1rem;
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-bottom: 18px;
        margin-bottom: 25px;
        border-bottom: 1px solid var(--border);
    }

    .brand-icon {
        width: 42px;
        height: 42px;
        border: 1px solid #3f3f46;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #18181b;
        color: #fafafa;
        font-size: 22px;
    }

    .brand-name {
        color: #fafafa;
        font-size: 15px;
        font-weight: 650;
        letter-spacing: -.4px;
    }

    .brand-subtitle {
        color: #71717a;
        font-size: 11px;
        margin-top: 3px;
    }

    .eyebrow {
        color: #a1a1aa;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .description {
        color: #a1a1aa;
        font-size: 14px;
        line-height: 1.8;
        margin-top: -5px;
        margin-bottom: 24px;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        color: #d4d4d8;
        border: 1px solid #27272a;
        background: #111113;
        border-radius: 999px;
        padding: 6px 11px;
        font-size: 11px;
    }

    .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #a1a1aa;
    }

    .section-label {
        color: #e4e4e7;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .muted-small {
        color: #71717a;
        font-size: 12px;
        line-height: 1.8;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #0f0f12;
        border-color: var(--border) !important;
        border-radius: 10px;
    }

    [data-testid="stFileUploader"] {
        background: #0f0f12;
        border: 1px dashed #3f3f46;
        border-radius: 10px;
        padding: 10px;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: transparent;
        border: none;
    }

    [data-testid="stMetric"] {
        background: #111113;
        border: 1px solid var(--border);
        border-radius: 9px;
        padding: 12px 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #a1a1aa;
        font-size: 12px;
    }

    [data-testid="stMetricValue"] {
        color: #fafafa;
        font-size: 20px;
        font-weight: 600;
    }

    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div {
        background: #111113;
        border-color: #27272a;
        border-radius: 8px;
        color: #fafafa;
    }

    [data-testid="stSlider"] {
        padding-top: 2px;
    }

    [data-testid="stButton"] button,
    [data-testid="stDownloadButton"] button {
        min-height: 40px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 550;
        transition: all .15s ease;
    }

    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button[kind="primary"] {
        background: #fafafa;
        color: #09090b;
        border: 1px solid #fafafa;
    }

    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stDownloadButton"] button[kind="primary"]:hover {
        background: #d4d4d8;
        color: #09090b;
        border-color: #d4d4d8;
    }

    [data-testid="stButton"] button[kind="secondary"] {
        background: #111113;
        color: #e4e4e7;
        border: 1px solid #27272a;
    }

    [data-testid="stButton"] button[kind="secondary"]:hover {
        background: #18181b;
        border-color: #52525b;
        color: #fafafa;
    }

    [data-testid="stImage"] img {
        border-radius: 8px;
    }

    [data-testid="stAlert"],
    [data-testid="stExpander"] {
        background: #111113;
        border: 1px solid #27272a;
        border-radius: 9px;
    }

    hr {
        border-color: #27272a;
    }

    .footer {
        border-top: 1px solid #27272a;
        padding-top: 18px;
        margin-top: 35px;
        color: #52525b;
        font-size: 11px;
        display: flex;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
    }

    @media (max-width: 768px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1.2rem 1rem 3rem;
        }
        h1 {
            font-size: 1.65rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# IMAGE UTILITIES
# =========================================================
@st.cache_data(show_spinner=False)
def convert_heic_to_jpeg(image_bytes: bytes) -> bytes | None:
    """Convert HEIC/HEIF images to JPEG in memory."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=95)
            return output.getvalue()
    except Exception:
        return None


def make_rgb(image: Image.Image) -> Image.Image:
    """Flatten transparency onto white for JPEG export."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def encode_image(image: Image.Image, output_format: str, quality: int) -> bytes:
    """Encode an image in the selected format."""
    output = io.BytesIO()
    save_image = image.copy()
    options = {}

    if output_format == "JPEG":
        save_image = make_rgb(save_image)
        options.update(quality=quality, optimize=True)
    elif output_format == "WEBP":
        options["quality"] = quality
    elif output_format == "PNG":
        options["optimize"] = True

    save_image.save(output, format=output_format, **options)
    return output.getvalue()


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="brand-row">
        <div class="brand-icon">✳</div>
        <div>
            <div class="brand-name">Pixel Studio</div>
            <div class="brand-subtitle">Image editing workspace</div>
        </div>
    </div>
    <div class="eyebrow">Creative tools / Image editor</div>
    """,
    unsafe_allow_html=True,
)

header_col, status_col = st.columns([3, 1])

with header_col:
    st.title("Image Editor")
    st.markdown(
        '<div class="description">'
        'Transform, enhance, and export your images in one simple workspace.'
        '</div>',
        unsafe_allow_html=True,
    )

with status_col:
    st.markdown(
        '<div style="text-align:right;padding-top:12px">'
        '<span class="pill"><span class="dot"></span>Ready to edit</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# UPLOAD
# =========================================================
with st.container(border=True):
    upload_col, formats_col = st.columns([2, 1])

    with upload_col:
        st.markdown(
            '<div class="section-label">Import image</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload PNG, JPG, WEBP, HEIC, or HEIF",
            type=["png", "jpg", "jpeg", "webp", "heic", "heif"],
            key="image_upload",
        )

    with formats_col:
        st.markdown(
            '<div class="section-label">Supported formats</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="muted-small">
                <b style="color:#d4d4d8">PNG</b> · Lossless quality<br>
                <b style="color:#d4d4d8">JPEG</b> · Photographs<br>
                <b style="color:#d4d4d8">WEBP</b> · Web optimized<br>
                <b style="color:#d4d4d8">HEIC / HEIF</b> · Apple images
            </div>
            """,
            unsafe_allow_html=True,
        )

if uploaded_file is None:
    _, empty_col, _ = st.columns([1, 2, 1])
    with empty_col:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align:center;padding:32px 12px">
                    <div style="font-size:38px;margin-bottom:14px">✳</div>
                    <div style="color:#fafafa;font-size:17px;font-weight:600">
                        Your canvas is waiting
                    </div>
                    <div style="color:#71717a;font-size:12px;line-height:1.8;margin-top:8px">
                        Upload an image above to access the editing tools,
                        filters, and export options.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="footer"><span>✳ PIXEL STUDIO</span>'
        '<span>Image editing workspace</span></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# =========================================================
# LOAD ORIGINAL IMAGE
# =========================================================
original_bytes = uploaded_file.getvalue()
file_extension = os.path.splitext(uploaded_file.name)[1].lower()

try:
    if file_extension in (".heic", ".heif"):
        with st.spinner("Converting HEIC/HEIF image..."):
            converted_bytes = convert_heic_to_jpeg(original_bytes)

        if converted_bytes is None:
            st.error("Unable to open this HEIC/HEIF image.")
            st.stop()

        image = Image.open(io.BytesIO(converted_bytes))
    else:
        image = Image.open(io.BytesIO(original_bytes))

    image.load()
    original_image = ImageOps.exif_transpose(image).copy()

except Exception as error:
    st.error(f"Unable to open image: {error}")
    st.stop()

original_width, original_height = original_image.size

# =========================================================
# ORIGINAL IMAGE METADATA
# =========================================================
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Width", f"{original_width:,} px")
with m2:
    st.metric("Height", f"{original_height:,} px")
with m3:
    st.metric("File size", f"{len(original_bytes) / 1024:.1f} KB")
with m4:
    st.metric("Color mode", original_image.mode)

with st.expander("View image metadata (EXIF)"):
    exif_data = original_image.getexif()

    if exif_data:
        exif_dict = {}
        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            exif_dict[str(tag_name)] = value
        st.json(exif_dict)
    else:
        st.caption("No EXIF metadata found.")

# =========================================================
# SIDEBAR CONTROLS
# Explicit widget keys make reset behavior reliable.
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div class="brand-row">
            <div class="brand-icon">✳</div>
            <div>
                <div class="brand-name">Editor controls</div>
                <div class="brand-subtitle">Adjust your image</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("01 — Transform")

    rotation = st.select_slider(
        "Rotation",
        options=[0, 90, 180, 270],
        value=0,
        format_func=lambda x: f"{x}°",
        key="rotation",
    )

    custom_rotation_enabled = st.checkbox(
        "Use custom rotation",
        key="custom_rotation_enabled",
    )

    if custom_rotation_enabled:
        custom_rotation = st.slider(
            "Custom angle",
            0, 359, 0,
            key="custom_rotation",
        )
        rotation = custom_rotation

    scale = st.select_slider(
        "Image scale",
        options=[25, 50, 75, 100, 125, 150, 200],
        value=100,
        format_func=lambda x: f"{x}%",
        key="scale",
    )

    custom_scale_enabled = st.checkbox(
        "Use custom scale",
        key="custom_scale_enabled",
    )

    if custom_scale_enabled:
        scale = st.slider(
            "Custom scale (%)",
            1, 500, 100,
            key="custom_scale",
        )

    st.divider()
    st.subheader("02 — Adjust")

    brightness = st.slider(
        "Brightness", 0.0, 2.0, 1.0, 0.1, key="brightness"
    )
    contrast = st.slider(
        "Contrast", 0.0, 2.0, 1.0, 0.1, key="contrast"
    )
    saturation = st.slider(
        "Saturation", 0.0, 2.0, 1.0, 0.1, key="saturation"
    )
    sharpness = st.slider(
        "Sharpness", 0.0, 2.0, 1.0, 0.1, key="sharpness"
    )

    st.divider()
    st.subheader("03 — Effects")

    blur_enabled = st.toggle("Gaussian blur", key="blur_enabled")

    blur_radius = 2.0
    if blur_enabled:
        blur_radius = st.slider(
            "Blur radius", 0.0, 10.0, 2.0, 0.5, key="blur_radius"
        )

    edge_enabled = st.toggle("Edge detection", key="edge_enabled")
    invert_enabled = st.toggle("Invert colors", key="invert_enabled")
    grayscale_enabled = st.toggle("Grayscale", key="grayscale_enabled")
    posterize_enabled = st.toggle("Posterize", key="posterize_enabled")

    posterize_bits = 4
    if posterize_enabled:
        posterize_bits = st.slider(
            "Posterize bits", 1, 8, 4, key="posterize_bits"
        )

    solarize_enabled = st.toggle("Solarize", key="solarize_enabled")

    solarize_threshold = 128
    if solarize_enabled:
        solarize_threshold = st.slider(
            "Solarize threshold",
            0, 255, 128,
            key="solarize_threshold",
        )

    st.divider()

    st.button(
        "↺ Reset all adjustments",
        key="reset_editor_button",
        use_container_width=True,
        on_click=reset_editor,
    )

    st.caption("Reset restores all editing controls to their defaults.")

   

# =========================================================
# APPLY ADJUSTMENTS FROM ORIGINAL IMAGE
# =========================================================
image = original_image.copy()

if rotation:
    image = image.rotate(rotation, expand=True)

if scale != 100:
    new_width = max(1, int(image.width * scale / 100))
    new_height = max(1, int(image.height * scale / 100))
    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS,
    )

if brightness != 1.0:
    image = ImageEnhance.Brightness(image).enhance(brightness)

if contrast != 1.0:
    image = ImageEnhance.Contrast(image).enhance(contrast)

if saturation != 1.0:
    image = ImageEnhance.Color(image).enhance(saturation)

if sharpness != 1.0:
    image = ImageEnhance.Sharpness(image).enhance(sharpness)

if blur_enabled:
    image = image.filter(ImageFilter.GaussianBlur(blur_radius))

if edge_enabled:
    image = image.filter(ImageFilter.FIND_EDGES)

if invert_enabled:
    image = ImageOps.invert(make_rgb(image))

if grayscale_enabled:
    image = ImageOps.grayscale(image)

if posterize_enabled:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image = ImageOps.posterize(image, posterize_bits)

if solarize_enabled:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image = ImageOps.solarize(image, solarize_threshold)

# =========================================================
# PREVIEW AND EXPORT
# =========================================================
st.markdown("")
preview_title, preview_status = st.columns([3, 1])

with preview_title:
    st.subheader("Canvas")

with preview_status:
    st.markdown(
        '<div style="text-align:right;padding-top:8px">'
        '<span class="pill"><span class="dot"></span>Live preview</span>'
        '</div>',
        unsafe_allow_html=True,
    )

preview_col, export_col = st.columns([1.8, 1], gap="large")

with preview_col:
    with st.container(border=True):
        st.markdown(
            '<div class="section-label">Preview / Current adjustments</div>',
            unsafe_allow_html=True,
        )
        st.image(image, width="stretch")
        st.divider()
        st.caption(
            f"{image.width:,} × {image.height:,} pixels · {image.mode}"
        )

with export_col:
    with st.container(border=True):
        st.markdown("### Export image")
        st.markdown(
            '<div class="muted-small">Choose a format and quality '
            'for your edited image.</div>',
            unsafe_allow_html=True,
        )

        output_format = st.selectbox(
            "File format",
            ["PNG", "JPEG", "WEBP"],
            index=0,
            key="output_format",
        )

        quality = 95
        if output_format in ("JPEG", "WEBP"):
            quality = st.slider(
                "Export quality",
                10, 100, 95,
                key="export_quality",
            )

        st.caption("Your original uploaded file is not modified.")

        # Identify the exact settings used to prepare an export.
        current_signature = (
            uploaded_file.name,
            original_width,
            original_height,
            rotation,
            scale,
            brightness,
            contrast,
            saturation,
            sharpness,
            blur_enabled,
            blur_radius if blur_enabled else 0,
            edge_enabled,
            invert_enabled,
            grayscale_enabled,
            posterize_enabled,
            posterize_bits if posterize_enabled else 0,
            solarize_enabled,
            solarize_threshold if solarize_enabled else 0,
            output_format,
            quality,
        )

        if st.button(
            "Prepare export",
            type="primary",
            use_container_width=True,
            key="prepare_export_button",
        ):
            try:
                processed_bytes = encode_image(image, output_format, quality)
                st.session_state["export_bytes"] = processed_bytes
                st.session_state["export_format"] = output_format
                st.session_state["export_signature"] = current_signature
            except Exception as error:
                st.error(f"Could not prepare the export: {error}")

        # Do not show an outdated export after an edit or reset.
        processed_bytes = st.session_state.get("export_bytes")
        processed_format = st.session_state.get("export_format")
        prepared_signature = st.session_state.get("export_signature")

        if (
            processed_bytes
            and processed_format == output_format
            and prepared_signature == current_signature
        ):
            extension = output_format.lower()
            mime_types = {
                "PNG": "image/png",
                "JPEG": "image/jpeg",
                "WEBP": "image/webp",
            }

            st.success(
                f"Export ready · {len(processed_bytes) / (1024 * 1024):.2f} MB"
            )

            st.download_button(
                label=f"Download {extension.upper()}",
                data=processed_bytes,
                file_name=f"pixel-studio-edited.{extension}",
                mime=mime_types[output_format],
                type="primary",
                use_container_width=True,
            )
        else:
            st.caption("Prepare your export to enable the download.")

    with st.container(border=True):
        st.markdown("### Current adjustments")

        adjustments = []

        if rotation:
            adjustments.append(f"Rotation: {rotation}°")
        if scale != 100:
            adjustments.append(f"Scale: {scale}%")
        if brightness != 1.0:
            adjustments.append(f"Brightness: {brightness:.1f}×")
        if contrast != 1.0:
            adjustments.append(f"Contrast: {contrast:.1f}×")
        if saturation != 1.0:
            adjustments.append(f"Saturation: {saturation:.1f}×")
        if sharpness != 1.0:
            adjustments.append(f"Sharpness: {sharpness:.1f}×")
        if blur_enabled:
            adjustments.append("Gaussian blur")
        if edge_enabled:
            adjustments.append("Edge detection")
        if invert_enabled:
            adjustments.append("Inverted colors")
        if grayscale_enabled:
            adjustments.append("Grayscale")
        if posterize_enabled:
            adjustments.append(f"Posterize ({posterize_bits} bits)")
        if solarize_enabled:
            adjustments.append(f"Solarize ({solarize_threshold})")

        if adjustments:
            for item in adjustments:
                st.markdown(
                    f'<div style="border:1px solid #27272a;'
                    f'background:#111113;border-radius:7px;'
                    f'padding:8px 10px;margin-bottom:7px;'
                    f'color:#d4d4d8;font-size:12px;">{item}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="muted-small">No adjustments applied. '
                'Your image is unchanged.</div>',
                unsafe_allow_html=True,
            )

# =========================================================
# FOOTER
# =========================================================
st.markdown(
    '<div class="footer"><span>✳ PIXEL STUDIO</span>'
    '<span>Image editing workspace · PNG · JPEG · WEBP</span></div>',
    unsafe_allow_html=True,
)
