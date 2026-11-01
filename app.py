
from __future__ import annotations

import base64
import copy
import io
import tempfile
from pathlib import Path

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    ImageFilter,
    ImageDraw,
    ImageFont,
    ImageColor,
)

# ============================================================
# OPTIONAL LIBRARIES
# ============================================================

try:
    import cv2
    CV2_AVAILABLE = True
    CV2_ERROR = None
except Exception as exc:
    cv2 = None
    CV2_AVAILABLE = False
    CV2_ERROR = str(exc)

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_AVAILABLE = True
except Exception:
    HEIC_AVAILABLE = False

try:
    from streamlit_drawable_konva import st_canvas
    CANVAS_AVAILABLE = True
    CANVAS_ERROR = None
except Exception as exc:
    st_canvas = None
    CANVAS_AVAILABLE = False
    CANVAS_ERROR = str(exc)

try:
    from streamlit_image_comparison import image_comparison
    COMPARISON_AVAILABLE = True
    COMPARISON_ERROR = None
except Exception as exc:
    image_comparison = None
    COMPARISON_AVAILABLE = False
    COMPARISON_ERROR = str(exc)


# ============================================================
# DRAGGABLE WATERMARK COMPONENT
# Embedded in this file: no separate HTML file required.
# ============================================================

WATERMARK_COMPONENT_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 8px;
    background: #111113;
    color: #fafafa;
    font-family: Arial, sans-serif;
}

.editor {
    width: 100%;
    overflow: hidden;
    border: 1px solid #303036;
    border-radius: 12px;
    background: #18181b;
}

.toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 14px;
    border-bottom: 1px solid #303036;
    font-size: 11px;
    letter-spacing: 0.7px;
    color: #a1a1aa;
}

.status {
    color: #38bdf8;
}

canvas {
    display: block;
    width: 100%;
    height: auto;
    background: #18181b;
    touch-action: none;
    cursor: grab;
}

canvas:active {
    cursor: grabbing;
}

.help {
    padding: 10px 14px;
    color: #a1a1aa;
    font-size: 11px;
    line-height: 1.5;
}
</style>
</head>

<body>

<div class="editor">
    <div class="toolbar">
        <span>WATERMARK POSITION EDITOR</span>
        <span class="status" id="status">Drag to move</span>
    </div>

    <canvas id="editor"></canvas>

    <div class="help">
        Drag the watermark to reposition it. Drag the blue corner handle
        to resize it. Changes are saved when you release the pointer.
    </div>
</div>

<script>
const canvas = document.getElementById("editor");
const ctx = canvas.getContext("2d");
const statusText = document.getElementById("status");

let args = {};
let image = new Image();
let imageLoaded = false;

let dragging = false;
let resizing = false;

let pointerOffset = {x: 0, y: 0};
let resizeStart = {
    distance: 1,
    scale: 1
};

let state = {
    x: 0.5,
    y: 0.5,
    scale: 1
};

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function getTextMetrics() {
    const ratio = canvas.width / image.width;

    const fontSize = Math.max(
        8,
        Number(args.font_size || 48) * ratio * state.scale
    );

    ctx.font = `bold ${fontSize}px Arial`;

    const lines = String(args.text || "").split("\n");
    const lineHeight = fontSize * 1.25;

    const widths = lines.map(
        line => ctx.measureText(line).width
    );

    return {
        fontSize,
        lines,
        lineHeight,
        width: Math.max(20, ...widths),
        height: Math.max(lineHeight, lines.length * lineHeight)
    };
}

function getBounds() {
    const metrics = getTextMetrics();

    const x = state.x * canvas.width;
    const y = state.y * canvas.height;

    return {
        left: x - metrics.width / 2 - 9,
        right: x + metrics.width / 2 + 9,
        top: y - metrics.height / 2 - 9,
        bottom: y + metrics.height / 2 + 9,
        handleX: x + metrics.width / 2 + 9,
        handleY: y + metrics.height / 2 + 9
    };
}

function draw() {
    if (!imageLoaded) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.drawImage(
        image,
        0,
        0,
        canvas.width,
        canvas.height
    );

    const text = String(args.text || "");

    if (!text) {
        ctx.fillStyle = "#ffffff";
        ctx.font = "14px Arial";
        ctx.textAlign = "center";

        ctx.fillText(
            "Enter watermark text in the settings panel",
            canvas.width / 2,
            canvas.height / 2
        );

        return;
    }

    const metrics = getTextMetrics();

    const x = state.x * canvas.width;
    const y = state.y * canvas.height;

    const opacity = clamp(
        Number(args.opacity ?? 100),
        0,
        100
    ) / 100;

    ctx.save();

    ctx.globalAlpha = opacity;
    ctx.font = `bold ${metrics.fontSize}px Arial`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const startY =
        y - ((metrics.lines.length - 1) * metrics.lineHeight) / 2;

    metrics.lines.forEach((line, index) => {
        const lineY = startY + index * metrics.lineHeight;

        if (args.outline) {
            ctx.lineWidth = Math.max(
                1,
                metrics.fontSize / 18
            );

            ctx.strokeStyle = "#000000";
            ctx.strokeText(line, x, lineY);
        }

        ctx.fillStyle = args.color || "#ffffff";
        ctx.fillText(line, x, lineY);
    });

    ctx.restore();

    // Selection outline
    const bounds = getBounds();

    ctx.save();

    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);

    ctx.strokeRect(
        bounds.left,
        bounds.top,
        bounds.right - bounds.left,
        bounds.bottom - bounds.top
    );

    ctx.setLineDash([]);

    // Resize handle
    ctx.fillStyle = "#38bdf8";

    ctx.beginPath();
    ctx.arc(
        bounds.handleX,
        bounds.handleY,
        8,
        0,
        Math.PI * 2
    );
    ctx.fill();

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.arc(
        bounds.handleX,
        bounds.handleY,
        3,
        0,
        Math.PI * 2
    );
    ctx.stroke();

    ctx.restore();
}

function resizeCanvas() {
    if (!imageLoaded) return;

    const availableWidth = Math.max(
        280,
        canvas.parentElement.clientWidth - 20
    );

    const ratio = Math.min(
        1,
        availableWidth / image.width
    );

    canvas.width = Math.max(
        1,
        Math.round(image.width * ratio)
    );

    canvas.height = Math.max(
        1,
        Math.round(image.height * ratio)
    );

    draw();
}

function getPointerPosition(event) {
    const rect = canvas.getBoundingClientRect();

    return {
        x: (event.clientX - rect.left) *
            (canvas.width / rect.width),

        y: (event.clientY - rect.top) *
            (canvas.height / rect.height)
    };
}

function sendValue() {
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: "streamlit:setComponentValue",
        value: {
            x: clamp(state.x, 0, 1),
            y: clamp(state.y, 0, 1),
            scale: clamp(state.scale, 0.2, 5)
        }
    }, "*");
}

canvas.addEventListener("pointerdown", event => {
    if (!imageLoaded || !args.text) return;

    const pointer = getPointerPosition(event);
    const bounds = getBounds();

    const handleDistance = Math.hypot(
        pointer.x - bounds.handleX,
        pointer.y - bounds.handleY
    );

    const insideText =
        pointer.x >= bounds.left &&
        pointer.x <= bounds.right &&
        pointer.y >= bounds.top &&
        pointer.y <= bounds.bottom;

    if (handleDistance <= 20) {
        resizing = true;
        dragging = false;

        const centerX = state.x * canvas.width;
        const centerY = state.y * canvas.height;

        resizeStart.distance = Math.max(
            1,
            Math.hypot(
                pointer.x - centerX,
                pointer.y - centerY
            )
        );

        resizeStart.scale = state.scale;

        statusText.textContent = "Resizing";
    } else if (insideText) {
        dragging = true;
        resizing = false;

        pointerOffset.x =
            pointer.x - state.x * canvas.width;

        pointerOffset.y =
            pointer.y - state.y * canvas.height;

        statusText.textContent = "Moving";
    } else {
        return;
    }

    canvas.setPointerCapture(event.pointerId);
    event.preventDefault();
});

canvas.addEventListener("pointermove", event => {
    if (!dragging && !resizing) return;

    const pointer = getPointerPosition(event);

    if (dragging) {
        state.x = (
            pointer.x - pointerOffset.x
        ) / canvas.width;

        state.y = (
            pointer.y - pointerOffset.y
        ) / canvas.height;
    }

    if (resizing) {
        const centerX = state.x * canvas.width;
        const centerY = state.y * canvas.height;

        const distance = Math.max(
            1,
            Math.hypot(
                pointer.x - centerX,
                pointer.y - centerY
            )
        );

        state.scale = resizeStart.scale *
            (distance / resizeStart.distance);
    }

    state.x = clamp(state.x, 0, 1);
    state.y = clamp(state.y, 0, 1);
    state.scale = clamp(state.scale, 0.2, 5);

    draw();
    event.preventDefault();
});

function finishPointer() {
    if (dragging || resizing) {
        sendValue();
    }

    dragging = false;
    resizing = false;

    statusText.textContent = "Drag to move";
}

canvas.addEventListener("pointerup", finishPointer);
canvas.addEventListener("pointercancel", finishPointer);
canvas.addEventListener("lostpointercapture", finishPointer);

function loadArgs(newArgs) {
    args = newArgs || {};

    const incoming = args.watermark_state || {};

    state = {
        x: clamp(Number(incoming.x ?? 0.5), 0, 1),
        y: clamp(Number(incoming.y ?? 0.5), 0, 1),
        scale: clamp(Number(incoming.scale ?? 1), 0.2, 5)
    };

    imageLoaded = false;

    image = new Image();

    image.onload = () => {
        imageLoaded = true;
        resizeCanvas();
    };

    image.onerror = () => {
        statusText.textContent = "Image preview unavailable";
    };

    image.src = args.image || "";
}

window.addEventListener("message", event => {
    const message = event.data;

    if (
        !message ||
        message.type !== "streamlit:render"
    ) {
        return;
    }

    loadArgs(message.args);
});

window.addEventListener("resize", () => {
    if (imageLoaded) {
        resizeCanvas();
    }
});

window.parent.postMessage({
    isStreamlitMessage: true,
    type: "streamlit:componentReady",
    apiVersion: 1
}, "*");

window.parent.postMessage({
    isStreamlitMessage: true,
    type: "streamlit:setFrameHeight",
    height: 500
}, "*");
</script>

</body>
</html>
"""

# Create the component frontend in a temporary directory.
# This keeps the project to one Python file.
WATERMARK_COMPONENT_DIR = (
    Path(tempfile.gettempdir())
    / "pixel_studio_watermark_component"
)

WATERMARK_COMPONENT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

WATERMARK_COMPONENT_FILE = (
    WATERMARK_COMPONENT_DIR / "index.html"
)

try:
    WATERMARK_COMPONENT_FILE.write_text(
        WATERMARK_COMPONENT_HTML,
        encoding="utf-8",
    )

    watermark_editor = components.declare_component(
        "pixel_studio_watermark_editor",
        path=str(WATERMARK_COMPONENT_DIR),
    )

    WATERMARK_AVAILABLE = True
    WATERMARK_ERROR = None

except Exception as exc:
    watermark_editor = None
    WATERMARK_AVAILABLE = False
    WATERMARK_ERROR = str(exc)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Pixel Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "source_image": None,
    "working_image": None,
    "loaded_signature": None,
    "image_name": "Untitled",

    "undo_stack": [],
    "redo_stack": [],
    "canvas_json": None,

    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "sharpness": 1.0,
    "exposure": 0.0,
    "temperature": 0,
    "tint": 0,
    "highlights": 0,
    "shadows": 0,
    "vignette": 0,

    "filter_name": "Original",

    "canvas_tool": "Brush",
    "brush_width": 8,
    "brush_colour": "#FF3B30",

    "text_content": "",
    "text_size": 48,
    "text_color": "#FFFFFF",
    "text_x": 50,
    "text_y": 50,
    "text_scale": 1.0,
    "text_opacity": 100,
    "text_outline": True,

    "export_format": "PNG",
    "export_quality": 95,

    "rotation_choice": 90,
    "resize_width": 1000,
    "resize_height": 700,
    "preserve_ratio": True,

    "crop_left": 0,
    "crop_top": 0,
    "crop_right": 100,
    "crop_bottom": 100,

    "crop_error": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = copy.deepcopy(value)


# ============================================================
# IMAGE UTILITIES
# ============================================================

def to_rgb(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new(
            "RGBA",
            rgba.size,
            "white",
        )
        background.alpha_composite(rgba)
        return background.convert("RGB")

    return image.convert("RGB")


def make_preview(
    image,
    max_width=1100,
    max_height=760,
):
    preview = image.copy()

    preview.thumbnail(
        (max_width, max_height),
        Image.Resampling.LANCZOS,
    )

    return preview


def get_font(size):
    paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/seguisb.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def clamp_image(array):
    return np.clip(array, 0, 255).astype(np.uint8)


# ============================================================
# BEFORE / AFTER COMPARISON
# ============================================================

def prepare_comparison_images(
    before,
    after,
    max_width=1100,
    max_height=760,
):
    before = to_rgb(before)
    after = to_rgb(after)

    target_width = min(
        max(before.width, after.width),
        max_width,
    )

    target_height = min(
        max(before.height, after.height),
        max_height,
    )

    canvas_width = max(1, target_width)
    canvas_height = max(1, target_height)

    def fit_to_canvas(image):
        fitted = ImageOps.contain(
            image,
            (canvas_width, canvas_height),
            method=Image.Resampling.LANCZOS,
        )

        canvas = Image.new(
            "RGB",
            (canvas_width, canvas_height),
            "#171717",
        )

        x = (canvas_width - fitted.width) // 2
        y = (canvas_height - fitted.height) // 2

        canvas.paste(fitted, (x, y))

        return canvas

    return (
        fit_to_canvas(before),
        fit_to_canvas(after),
    )


def render_before_after(
    after_image,
    section_name="comparison",
):
    before_image = st.session_state.source_image

    if before_image is None or after_image is None:
        st.info(
            "Upload an image to use Before / After comparison."
        )
        return

    before_image, after_image = prepare_comparison_images(
        before_image,
        after_image,
    )

    st.markdown("#### Before / After comparison")

    if COMPARISON_AVAILABLE:
        try:
            image_comparison(
                img1=before_image,
                img2=after_image,
                label1="BEFORE",
                label2="AFTER",
                width=900,
                starting_position=50,
                show_labels=True,
                make_responsive=True,
                in_memory=True,
            )

            st.caption(
                "Drag the vertical divider left or right "
                "to compare the original and edited image."
            )

            return

        except Exception as exc:
            st.warning(
                f"Interactive comparison unavailable: {exc}"
            )

    left, right = st.columns(2)

    with left:
        st.markdown("**BEFORE**")
        st.image(
            before_image,
            use_container_width=True,
        )

    with right:
        st.markdown("**AFTER**")
        st.image(
            after_image,
            use_container_width=True,
        )


# ============================================================
# HISTORY
# ============================================================

def save_history():
    image = st.session_state.working_image

    if image is None:
        return

    st.session_state.undo_stack.append(image.copy())

    if len(st.session_state.undo_stack) > 15:
        st.session_state.undo_stack.pop(0)

    st.session_state.redo_stack.clear()


def undo():
    if not st.session_state.undo_stack:
        return

    current = st.session_state.working_image

    if current is not None:
        st.session_state.redo_stack.append(current.copy())

    st.session_state.working_image = (
        st.session_state.undo_stack.pop()
    )

    st.session_state.canvas_json = None


def redo():
    if not st.session_state.redo_stack:
        return

    current = st.session_state.working_image

    if current is not None:
        st.session_state.undo_stack.append(current.copy())

    st.session_state.working_image = (
        st.session_state.redo_stack.pop()
    )

    st.session_state.canvas_json = None


# ============================================================
# RESET CALLBACKS
# ============================================================

def reset_adjustments():
    keys = [
        "brightness",
        "contrast",
        "saturation",
        "sharpness",
        "exposure",
        "temperature",
        "tint",
        "highlights",
        "shadows",
        "vignette",
    ]

    for key in keys:
        st.session_state[key] = copy.deepcopy(
            DEFAULTS[key]
        )

    st.session_state.filter_name = "Original"


def reset_adjustments_callback():
    reset_adjustments()


def reset_project():
    if st.session_state.source_image is not None:
        st.session_state.working_image = (
            st.session_state.source_image.copy()
        )

    st.session_state.undo_stack.clear()
    st.session_state.redo_stack.clear()
    st.session_state.canvas_json = None

    st.session_state.text_content = ""
    st.session_state.text_x = 50
    st.session_state.text_y = 50
    st.session_state.text_scale = 1.0
    st.session_state.text_opacity = 100

    st.session_state.crop_error = ""

    reset_adjustments()


def clear_text_callback():
    st.session_state.text_content = ""


def clear_drawing_callback():
    st.session_state.canvas_json = None


def set_filter_preset(preset):
    st.session_state.filter_name = preset


# ============================================================
# OPENCV PROCESSING
# ============================================================

def opencv_auto_enhance(image):
    if not CV2_AVAILABLE:
        return image

    rgb = np.asarray(to_rgb(image))

    lab = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2LAB,
    )

    lightness, channel_a, channel_b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced_lightness = clahe.apply(lightness)

    enhanced_lab = cv2.merge(
        (
            enhanced_lightness,
            channel_a,
            channel_b,
        )
    )

    result = cv2.cvtColor(
        enhanced_lab,
        cv2.COLOR_LAB2RGB,
    )

    return Image.fromarray(result)


def opencv_denoise(image):
    if not CV2_AVAILABLE:
        return image

    array = np.asarray(to_rgb(image))

    result = cv2.fastNlMeansDenoisingColored(
        array,
        None,
        6,
        6,
        7,
        21,
    )

    return Image.fromarray(result)


def opencv_edge_image(image):
    if not CV2_AVAILABLE:
        return image

    array = np.asarray(to_rgb(image))

    gray = cv2.cvtColor(
        array,
        cv2.COLOR_RGB2GRAY,
    )

    edges = cv2.Canny(
        gray,
        80,
        160,
    )

    return Image.fromarray(edges).convert("RGB")


def auto_enhance_callback():
    if (
        st.session_state.working_image is None
        or not CV2_AVAILABLE
    ):
        return

    save_history()

    st.session_state.working_image = opencv_auto_enhance(
        st.session_state.working_image
    )


def denoise_callback():
    if (
        st.session_state.working_image is None
        or not CV2_AVAILABLE
    ):
        return

    save_history()

    st.session_state.working_image = opencv_denoise(
        st.session_state.working_image
    )


# ============================================================
# ADJUSTMENT ENGINE
# ============================================================

def apply_adjustments(image):
    img = to_rgb(image)

    img = ImageEnhance.Brightness(img).enhance(
        float(st.session_state.brightness)
    )

    img = ImageEnhance.Contrast(img).enhance(
        float(st.session_state.contrast)
    )

    img = ImageEnhance.Color(img).enhance(
        float(st.session_state.saturation)
    )

    img = ImageEnhance.Sharpness(img).enhance(
        float(st.session_state.sharpness)
    )

    arr = np.asarray(img).astype(np.float32)

    # Exposure
    arr *= 2 ** float(st.session_state.exposure)

    # Temperature and tint
    temperature = int(st.session_state.temperature)
    tint = int(st.session_state.tint)

    arr[:, :, 0] += (
        temperature * 0.45
        + tint * 0.10
    )

    arr[:, :, 1] += tint * 0.30

    arr[:, :, 2] -= (
        temperature * 0.45
        - tint * 0.10
    )

    luminance = (
        0.2126 * arr[:, :, 0]
        + 0.7152 * arr[:, :, 1]
        + 0.0722 * arr[:, :, 2]
    ) / 255.0

    highlight_mask = np.clip(
        (luminance - 0.45) / 0.55,
        0,
        1,
    )

    shadow_mask = np.clip(
        (0.55 - luminance) / 0.55,
        0,
        1,
    )

    arr += (
        int(st.session_state.highlights)
        * highlight_mask[:, :, None]
    )

    arr += (
        int(st.session_state.shadows)
        * shadow_mask[:, :, None]
    )

    img = Image.fromarray(clamp_image(arr))

    # Vignette
    vignette = int(st.session_state.vignette)

    if vignette > 0:
        width, height = img.size

        y, x = np.ogrid[:height, :width]

        cx = (width - 1) / 2
        cy = (height - 1) / 2

        distance = np.sqrt(
            ((x - cx) / max(cx, 1)) ** 2
            + ((y - cy) / max(cy, 1)) ** 2
        )

        mask = np.clip(
            1 - distance * (vignette / 100) * 0.85,
            0.15,
            1,
        )

        pixels = np.asarray(img).astype(np.float32)
        pixels *= mask[:, :, None]

        img = Image.fromarray(
            clamp_image(pixels)
        )

    return img


# ============================================================
# FILTER ENGINE
# ============================================================

FILTERS = [
    "Original",
    "Black & White",
    "Sepia",
    "Vintage",
    "Warm",
    "Cool",
    "Dream",
    "Dramatic",
    "Blur",
    "Sharpen",
    "Emboss",
    "Edge",
    "Posterize",
    "Solarize",
    "Invert",
]


def apply_filter(image):
    img = to_rgb(image)
    name = st.session_state.filter_name

    if name == "Original":
        return img

    if name == "Black & White":
        return ImageOps.grayscale(img).convert("RGB")

    if name == "Sepia":
        gray = np.asarray(
            ImageOps.grayscale(img)
        ).astype(np.float32)

        result = np.zeros(
            (gray.shape[0], gray.shape[1], 3),
            dtype=np.float32,
        )

        result[:, :, 0] = gray * 1.08
        result[:, :, 1] = gray * 0.92
        result[:, :, 2] = gray * 0.72

        return Image.fromarray(
            clamp_image(result)
        )

    if name == "Vintage":
        img = ImageEnhance.Color(img).enhance(0.65)
        img = ImageEnhance.Contrast(img).enhance(0.90)

        arr = np.asarray(img).astype(np.float32)

        arr[:, :, 0] *= 1.06
        arr[:, :, 2] *= 0.88

        return Image.fromarray(
            clamp_image(arr)
        )

    if name == "Warm":
        arr = np.asarray(img).astype(np.float32)
        arr[:, :, 0] += 18
        arr[:, :, 2] -= 12

        return Image.fromarray(
            clamp_image(arr)
        )

    if name == "Cool":
        arr = np.asarray(img).astype(np.float32)
        arr[:, :, 0] -= 12
        arr[:, :, 2] += 18

        return Image.fromarray(
            clamp_image(arr)
        )

    if name == "Dream":
        img = ImageEnhance.Brightness(img).enhance(1.08)
        img = ImageEnhance.Color(img).enhance(0.85)

        return img.filter(
            ImageFilter.GaussianBlur(0.6)
        )

    if name == "Dramatic":
        img = ImageEnhance.Contrast(img).enhance(1.45)
        img = ImageEnhance.Color(img).enhance(1.15)

        return img.filter(
            ImageFilter.UnsharpMask(
                radius=2,
                percent=130,
                threshold=3,
            )
        )

    if name == "Blur":
        return img.filter(
            ImageFilter.GaussianBlur(2.5)
        )

    if name == "Sharpen":
        return img.filter(
            ImageFilter.UnsharpMask(
                radius=2,
                percent=180,
                threshold=3,
            )
        )

    if name == "Emboss":
        return img.filter(
            ImageFilter.EMBOSS
        ).convert("RGB")

    if name == "Edge":
        if CV2_AVAILABLE:
            return opencv_edge_image(img)

        return img.filter(
            ImageFilter.FIND_EDGES
        ).convert("RGB")

    if name == "Posterize":
        return ImageOps.posterize(img, bits=4)

    if name == "Solarize":
        return ImageOps.solarize(img, threshold=128)

    if name == "Invert":
        return ImageOps.invert(img)

    return img


# ============================================================
# TEXT AND WATERMARK ENGINE
# ============================================================

def add_text(image):
    text = str(
        st.session_state.text_content
    ).strip()

    if not text:
        return image.convert("RGB")

    img = image.convert("RGBA")
    draw = ImageDraw.Draw(img)

    base_size = int(st.session_state.text_size)
    scale = float(st.session_state.text_scale)

    size = max(
        1,
        round(base_size * scale),
    )

    # Position is the center of the watermark.
    x = round(
        img.width * int(st.session_state.text_x) / 100
    )

    y = round(
        img.height * int(st.session_state.text_y) / 100
    )

    font = get_font(size)

    opacity = max(
        0,
        min(100, int(st.session_state.text_opacity)),
    )

    red, green, blue = ImageColor.getrgb(
        st.session_state.text_color
    )

    alpha = round(255 * opacity / 100)

    fill = (
        red,
        green,
        blue,
        alpha,
    )

    outline = bool(st.session_state.text_outline)

    stroke_width = (
        max(1, size // 18)
        if outline else 0
    )

    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=fill,
        anchor="mm",
        align="center",
        spacing=max(2, size // 5),
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, alpha),
    )

    return img.convert("RGB")


def render_watermark_editor(image):
    if not WATERMARK_AVAILABLE:
        st.error(
            "The draggable watermark editor could not be loaded."
        )

        st.code(
            WATERMARK_ERROR or "Unknown component error"
        )

        return

    preview = make_preview(
        to_rgb(image),
        max_width=1000,
        max_height=700,
    )

    buffer = io.BytesIO()

    preview.save(
        buffer,
        format="JPEG",
        quality=88,
    )

    image_data = (
        "data:image/jpeg;base64,"
        + base64.b64encode(
            buffer.getvalue()
        ).decode("ascii")
    )

    result = watermark_editor(
        image=image_data,
        text=st.session_state.text_content,
        font_size=int(st.session_state.text_size),
        color=st.session_state.text_color,
        opacity=int(st.session_state.text_opacity),
        outline=bool(st.session_state.text_outline),
        watermark_state={
            "x": float(st.session_state.text_x) / 100,
            "y": float(st.session_state.text_y) / 100,
            "scale": float(st.session_state.text_scale),
        },
        key="pixel_studio_watermark_editor",
        default=None,
    )

    if isinstance(result, dict):
        try:
            st.session_state.text_x = max(
                0,
                min(
                    100,
                    round(float(result.get("x", 0.5)) * 100),
                ),
            )

            st.session_state.text_y = max(
                0,
                min(
                    100,
                    round(float(result.get("y", 0.5)) * 100),
                ),
            )

            st.session_state.text_scale = max(
                0.2,
                min(
                    5.0,
                    float(result.get("scale", 1.0)),
                ),
            )

        except (TypeError, ValueError):
            pass


# ============================================================
# DRAWING COMPOSITION
# ============================================================

def composite_drawing(
    image,
    drawing_data,
    canvas_size,
):
    base = image.convert("RGBA")

    if drawing_data is None:
        return base.convert("RGB")

    try:
        overlay_array = np.asarray(drawing_data)

        if (
            overlay_array.ndim != 3
            or overlay_array.shape[2] not in (3, 4)
        ):
            return base.convert("RGB")

        overlay = Image.fromarray(
            overlay_array.astype(np.uint8)
        ).convert("RGBA")

        if overlay.size != canvas_size:
            overlay = overlay.resize(
                canvas_size,
                Image.Resampling.LANCZOS,
            )

        if overlay.size != base.size:
            overlay = overlay.resize(
                base.size,
                Image.Resampling.LANCZOS,
            )

        base.alpha_composite(overlay)

        return base.convert("RGB")

    except Exception:
        return base.convert("RGB")


def get_adjusted_image():
    if st.session_state.working_image is None:
        raise ValueError("No image is loaded.")

    adjusted = apply_adjustments(
        st.session_state.working_image
    )

    return apply_filter(adjusted)


def make_final_image(
    drawing_data=None,
    canvas_size=None,
):
    image = get_adjusted_image()

    if canvas_size is None:
        canvas_size = image.size

    image = composite_drawing(
        image,
        drawing_data,
        canvas_size,
    )

    return add_text(image)


# ============================================================
# TRANSFORM HELPERS
# ============================================================

def apply_transform(operation):
    if st.session_state.working_image is None:
        return

    save_history()

    st.session_state.working_image = operation(
        st.session_state.working_image
    )

    st.session_state.canvas_json = None


def apply_rotation_callback():
    angle = int(
        st.session_state.rotation_choice
    )

    apply_transform(
        lambda image: image.rotate(
            -angle,
            expand=True,
            resample=Image.Resampling.BICUBIC,
        )
    )


def flip_horizontal_callback():
    apply_transform(ImageOps.mirror)


def flip_vertical_callback():
    apply_transform(ImageOps.flip)


def apply_resize_callback():
    image = st.session_state.working_image

    if image is None:
        return

    width = int(st.session_state.resize_width)
    height = int(st.session_state.resize_height)

    if st.session_state.preserve_ratio:
        ratio = image.width / image.height
        height = max(1, round(width / ratio))

    apply_transform(
        lambda source: source.resize(
            (width, height),
            Image.Resampling.LANCZOS,
        )
    )


def apply_crop_callback():
    image = st.session_state.working_image

    if image is None:
        return

    left = int(st.session_state.crop_left)
    top = int(st.session_state.crop_top)
    right = int(st.session_state.crop_right)
    bottom = int(st.session_state.crop_bottom)

    if right <= left or bottom <= top:
        st.session_state.crop_error = (
            "Right must be greater than left, and bottom "
            "must be greater than top."
        )
        return

    st.session_state.crop_error = ""

    box = (
        round(image.width * left / 100),
        round(image.height * top / 100),
        round(image.width * right / 100),
        round(image.height * bottom / 100),
    )

    apply_transform(
        lambda source: source.crop(box)
    )


# ============================================================
# UI HELPERS
# ============================================================

def section_title(title, description=None):
    st.subheader(title)

    if description:
        st.caption(description)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🎨 Pixel Studio")
    st.caption("CREATIVE IMAGE WORKSPACE")

    st.divider()

    st.markdown("**PROJECT**")

    uploaded = st.file_uploader(
        "Open image",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
            "bmp",
            "tif",
            "tiff",
            "heic",
            "heif",
        ],
        help="Upload a photo or image to begin editing.",
    )

    if uploaded is not None:
        signature = (
            uploaded.name,
            uploaded.size,
        )

        if (
            st.session_state.loaded_signature
            != signature
        ):
            try:
                with Image.open(uploaded) as opened:
                    image = to_rgb(opened)

                st.session_state.source_image = image.copy()
                st.session_state.working_image = image.copy()

                st.session_state.image_name = Path(
                    uploaded.name
                ).stem

                st.session_state.loaded_signature = signature

                st.session_state.undo_stack.clear()
                st.session_state.redo_stack.clear()
                st.session_state.canvas_json = None

                st.session_state.text_content = ""
                st.session_state.text_x = 50
                st.session_state.text_y = 50
                st.session_state.text_scale = 1.0
                st.session_state.text_opacity = 100

                reset_adjustments()

                st.session_state.resize_width = image.width
                st.session_state.resize_height = image.height

                st.session_state.crop_left = 0
                st.session_state.crop_top = 0
                st.session_state.crop_right = 100
                st.session_state.crop_bottom = 100

            except Exception as exc:
                st.error(
                    f"Could not open image: {exc}"
                )

    if st.session_state.working_image is None:
        st.info("Upload an image to begin.")
        st.stop()

    working = st.session_state.working_image

    st.success(
        f"Loaded: {st.session_state.image_name}"
    )

    st.caption(
        f"{working.width:,} × {working.height:,} px"
    )

    st.divider()

    st.markdown("**HISTORY**")

    undo_col, redo_col = st.columns(2)

    with undo_col:
        st.button(
            "↶ Undo",
            use_container_width=True,
            disabled=not st.session_state.undo_stack,
            on_click=undo,
        )

    with redo_col:
        st.button(
            "↷ Redo",
            use_container_width=True,
            disabled=not st.session_state.redo_stack,
            on_click=redo,
        )

    st.button(
        "Reset project",
        use_container_width=True,
        on_click=reset_project,
    )

    st.divider()

    st.markdown("**QUICK ACTIONS**")

    st.button(
        "Reset adjustments",
        use_container_width=True,
        on_click=reset_adjustments_callback,
    )

    st.button(
        "Clear drawing",
        use_container_width=True,
        on_click=clear_drawing_callback,
    )

    st.divider()

    st.markdown("**PROCESSING ENGINE**")

    st.caption(
        "OpenCV: Available"
        if CV2_AVAILABLE
        else "OpenCV: Not installed"
    )

    st.caption(
        "HEIC support: Available"
        if HEIC_AVAILABLE
        else "HEIC support: Not installed"
    )

    st.caption(
        "Drawing canvas: Available"
        if CANVAS_AVAILABLE
        else "Drawing canvas: Not installed"
    )

    st.caption(
        "Image comparison: Available"
        if COMPARISON_AVAILABLE
        else "Image comparison: Not installed"
    )

    st.caption(
        "Draggable watermark: Available"
        if WATERMARK_AVAILABLE
        else "Draggable watermark: Not available"
    )

    st.divider()

    st.caption(
        "Pixel Studio · Image editing workspace"
    )


# ============================================================
# HEADER
# ============================================================

working = st.session_state.working_image
adjusted = get_adjusted_image()

header_left, header_middle, header_right = st.columns(
    [2.4, 1, 1]
)

with header_left:
    st.title(st.session_state.image_name)
    st.caption("Pixel Studio  /  Image Editor")

with header_middle:
    st.metric(
        "Canvas width",
        f"{working.width:,} px",
    )

with header_right:
    st.metric(
        "Canvas height",
        f"{working.height:,} px",
    )

st.divider()


# ============================================================
# EDITOR NAVIGATION
# ============================================================

(
    workspace_tab,
    adjustment_tab,
    filter_tab,
    transform_tab,
    text_tab,
    export_tab,
) = st.tabs(
    [
        "🖼️ Workspace",
        "☀️ Adjustments",
        "🎞️ Filters",
        "✂️ Transform",
        "🔤 Text",
        "📤 Export",
    ]
)


# ============================================================
# WORKSPACE
# ============================================================

drawing_data = None
canvas_dimensions = adjusted.size

with workspace_tab:
    section_title(
        "Editing canvas",
        "Draw, annotate, add shapes and preview your image.",
    )

    if not CANVAS_AVAILABLE:
        st.error(
            "The drawing component could not be loaded."
        )

        st.code(
            CANVAS_ERROR or "Unknown component error"
        )

    else:
        tool_labels = {
            "Brush": "freedraw",
            "Line": "line",
            "Rectangle": "rect",
            "Circle": "circle",
            "Point": "point",
            "Polygon": "polygon",
            "Spline": "spline",
            "Crop selection": "rect_crop",
            "Move / Transform": "transform",
            "Pan canvas": "pan",
        }

        toolbar_col, stroke_col, colour_col = st.columns(
            [1.5, 1, 1]
        )

        with toolbar_col:
            selected_tool = st.selectbox(
                "Active tool",
                list(tool_labels.keys()),
                key="canvas_tool",
            )

        with stroke_col:
            stroke_width = st.number_input(
                "Stroke size",
                min_value=1,
                max_value=100,
                step=1,
                key="brush_width",
            )

        with colour_col:
            stroke_colour = st.color_picker(
                "Stroke colour",
                key="brush_colour",
            )

        background = make_preview(adjusted)

        canvas_dimensions = background.size

        try:
            result = st_canvas(
                fill_color=stroke_colour + "44",
                stroke_width=int(stroke_width),
                stroke_color=stroke_colour,
                background_image=background,
                background_color="#171717",
                height=background.height,
                width=background.width,
                drawing_mode=tool_labels[selected_tool],
                initial_drawing=st.session_state.canvas_json,
                update_streamlit=True,
                display_toolbar=True,
                tools=[
                    "freedraw",
                    "line",
                    "rect",
                    "rect_crop",
                    "circle",
                    "point",
                    "polygon",
                    "spline",
                    "transform",
                    "pan",
                ],
                display_tool_picker=False,
                display_color_pickers=False,
                enable_viewport_controls=True,
                key="pixel_studio_canvas",
            )

            if result is not None:
                if result.json_data is not None:
                    st.session_state.canvas_json = (
                        result.json_data
                    )

                drawing_data = result.image_data

        except Exception as exc:
            st.error(
                f"Canvas error: {exc}"
            )

    final_preview = make_final_image(
        drawing_data,
        canvas_dimensions,
    )

    st.divider()

    render_before_after(
        final_preview,
        "workspace_comparison",
    )

    st.divider()

    preview_col, info_col = st.columns(
        [2.2, 1]
    )

    with preview_col:
        st.markdown("**LIVE PREVIEW**")

        st.image(
            final_preview,
            use_container_width=True,
        )

    with info_col:
        with st.container(border=True):
            st.markdown("**DOCUMENT INFO**")

            st.write(
                f"Name: {st.session_state.image_name}"
            )

            st.write(
                f"Width: {working.width:,} px"
            )

            st.write(
                f"Height: {working.height:,} px"
            )

            st.write(
                f"Filter: {st.session_state.filter_name}"
            )

        with st.container(border=True):
            st.markdown("**APPLY YOUR EDITS**")

            st.caption(
                "Commit the current preview to your working image. "
                "The previous image is saved in history."
            )

            if st.button(
                "Apply edits to image",
                type="primary",
                use_container_width=True,
            ):
                save_history()

                st.session_state.working_image = (
                    final_preview.copy()
                )

                st.session_state.canvas_json = None
                st.session_state.text_content = ""

                reset_adjustments()

                st.rerun()


# ============================================================
# ADJUSTMENTS
# ============================================================

with adjustment_tab:
    section_title(
        "Light and colour",
        "Precise numeric controls and automatic image processing.",
    )

    light_col, colour_col = st.columns(2)

    with light_col:
        with st.container(border=True):
            st.markdown("#### Light")

            st.number_input(
                "Brightness",
                min_value=0.0,
                max_value=2.0,
                step=0.05,
                key="brightness",
                format="%.2f",
            )

            st.number_input(
                "Contrast",
                min_value=0.0,
                max_value=2.0,
                step=0.05,
                key="contrast",
                format="%.2f",
            )

            st.number_input(
                "Exposure",
                min_value=-2.0,
                max_value=2.0,
                step=0.1,
                key="exposure",
                format="%.1f",
            )

            st.number_input(
                "Highlights",
                min_value=-100,
                max_value=100,
                step=5,
                key="highlights",
            )

            st.number_input(
                "Shadows",
                min_value=-100,
                max_value=100,
                step=5,
                key="shadows",
            )

    with colour_col:
        with st.container(border=True):
            st.markdown("#### Colour and detail")

            st.number_input(
                "Saturation",
                min_value=0.0,
                max_value=2.0,
                step=0.05,
                key="saturation",
                format="%.2f",
            )

            st.number_input(
                "Sharpness",
                min_value=0.0,
                max_value=3.0,
                step=0.05,
                key="sharpness",
                format="%.2f",
            )

            st.number_input(
                "Temperature",
                min_value=-100,
                max_value=100,
                step=5,
                key="temperature",
            )

            st.number_input(
                "Tint",
                min_value=-100,
                max_value=100,
                step=5,
                key="tint",
            )

            st.number_input(
                "Vignette",
                min_value=0,
                max_value=100,
                step=5,
                key="vignette",
            )

    st.divider()

    st.markdown("#### AI-assisted image processing")

    auto_col, denoise_col, reset_col = st.columns(3)

    with auto_col:
        st.button(
            "✨ Auto enhance",
            use_container_width=True,
            disabled=not CV2_AVAILABLE,
            on_click=auto_enhance_callback,
        )

    with denoise_col:
        st.button(
            "Reduce noise",
            use_container_width=True,
            disabled=not CV2_AVAILABLE,
            on_click=denoise_callback,
        )

    with reset_col:
        st.button(
            "Reset values",
            use_container_width=True,
            on_click=reset_adjustments_callback,
        )

    if not CV2_AVAILABLE:
        st.info(
            "Install opencv-python-headless to enable "
            "automatic enhancement and denoising."
        )

    st.divider()

    adjustment_preview = get_adjusted_image()

    render_before_after(
        adjustment_preview,
        "adjustment_comparison",
    )

    st.markdown("**ADJUSTMENT PREVIEW**")

    st.image(
        adjustment_preview,
        use_container_width=True,
    )


# ============================================================
# FILTERS
# ============================================================

with filter_tab:
    section_title(
        "Creative filters",
        "Choose a preset to change the mood of your image.",
    )

    st.selectbox(
        "Filter preset",
        FILTERS,
        key="filter_name",
    )

    st.markdown("#### Quick presets")

    preset_names = [
        "Original",
        "Black & White",
        "Sepia",
        "Vintage",
        "Warm",
        "Cool",
        "Dream",
        "Dramatic",
    ]

    preset_columns = st.columns(4)

    for index, preset in enumerate(preset_names):
        with preset_columns[index % 4]:
            st.button(
                preset,
                key=f"preset_{index}",
                use_container_width=True,
                on_click=set_filter_preset,
                args=(preset,),
            )

    st.divider()

    filter_preview = get_adjusted_image()

    render_before_after(
        filter_preview,
        "filter_comparison",
    )

    st.markdown("**FILTER PREVIEW**")

    st.image(
        filter_preview,
        use_container_width=True,
    )


# ============================================================
# TRANSFORM
# ============================================================

with transform_tab:
    section_title(
        "Transform image",
        "Rotate, flip, resize and crop your working image.",
    )

    rotate_col, flip_col = st.columns(2)

    with rotate_col:
        with st.container(border=True):
            st.markdown("#### Rotate")

            st.selectbox(
                "Rotation angle",
                [90, 180, 270, 5, -5, 15, -15, 45, -45],
                format_func=lambda value: f"{value}°",
                key="rotation_choice",
            )

            st.button(
                "Apply rotation",
                use_container_width=True,
                on_click=apply_rotation_callback,
            )

    with flip_col:
        with st.container(border=True):
            st.markdown("#### Flip")

            st.button(
                "Flip horizontally",
                use_container_width=True,
                on_click=flip_horizontal_callback,
            )

            st.button(
                "Flip vertically",
                use_container_width=True,
                on_click=flip_vertical_callback,
            )

    st.divider()

    with st.container(border=True):
        st.markdown("#### Resize")

        resize_col1, resize_col2, resize_col3 = st.columns(3)

        with resize_col1:
            st.number_input(
                "New width (px)",
                min_value=1,
                max_value=12000,
                key="resize_width",
            )

        with resize_col2:
            st.number_input(
                "New height (px)",
                min_value=1,
                max_value=12000,
                key="resize_height",
            )

        with resize_col3:
            st.checkbox(
                "Keep aspect ratio",
                key="preserve_ratio",
            )

        st.button(
            "Apply resize",
            type="primary",
            use_container_width=True,
            on_click=apply_resize_callback,
        )

    st.divider()

    with st.container(border=True):
        st.markdown("#### Crop")

        st.caption(
            "Set crop boundaries as percentages of the image dimensions."
        )

        crop_left_col, crop_right_col = st.columns(2)

        with crop_left_col:
            st.number_input(
                "Left (%)",
                min_value=0,
                max_value=99,
                key="crop_left",
            )

            st.number_input(
                "Top (%)",
                min_value=0,
                max_value=99,
                key="crop_top",
            )

        with crop_right_col:
            st.number_input(
                "Right (%)",
                min_value=1,
                max_value=100,
                key="crop_right",
            )

            st.number_input(
                "Bottom (%)",
                min_value=1,
                max_value=100,
                key="crop_bottom",
            )

        st.button(
            "Apply crop",
            type="primary",
            use_container_width=True,
            on_click=apply_crop_callback,
        )

        if st.session_state.get("crop_error"):
            st.error(
                st.session_state.crop_error
            )

    st.divider()

    render_before_after(
        get_adjusted_image(),
        "transform_comparison",
    )


# ============================================================
# TEXT AND WATERMARK
# ============================================================

with text_tab:
    section_title(
        "Text and watermark",
        "Drag your watermark directly on the image. "
        "Use its corner handle to resize it.",
    )

    settings_col, preview_col = st.columns(
        [1, 1.5]
    )

    with settings_col:
        with st.container(border=True):
            st.markdown("#### Watermark settings")

            st.text_area(
                "Text content",
                key="text_content",
                placeholder="Type your text here...",
                height=110,
            )

            st.number_input(
                "Font size",
                min_value=8,
                max_value=250,
                step=2,
                key="text_size",
            )

            st.color_picker(
                "Text colour",
                key="text_color",
            )

            st.number_input(
                "Opacity (%)",
                min_value=0,
                max_value=100,
                step=5,
                key="text_opacity",
            )

            st.checkbox(
                "Add dark outline",
                key="text_outline",
            )

            st.divider()

            st.markdown("#### Position and size")

            st.caption(
                f"Horizontal: {st.session_state.text_x}%"
            )

            st.caption(
                f"Vertical: {st.session_state.text_y}%"
            )

            st.caption(
                f"Scale: {st.session_state.text_scale:.2f}×"
            )

            if st.button(
                "Reset watermark position and size",
                use_container_width=True,
            ):
                st.session_state.text_x = 50
                st.session_state.text_y = 50
                st.session_state.text_scale = 1.0
                st.rerun()

            st.button(
                "Clear text",
                use_container_width=True,
                on_click=clear_text_callback,
            )

    with preview_col:
        st.markdown("#### Drag-and-drop watermark editor")

        render_watermark_editor(
            get_adjusted_image()
        )

        st.divider()

        st.markdown("#### Final watermark preview")

        text_preview = add_text(
            get_adjusted_image()
        )

        st.image(
            text_preview,
            use_container_width=True,
        )

    render_before_after(
        add_text(get_adjusted_image()),
        "text_comparison",
    )


# ============================================================
# EXPORT
# ============================================================

with export_tab:
    section_title(
        "Export your image",
        "Choose a format and download your finished work.",
    )

    export_image = make_final_image(
        drawing_data,
        canvas_dimensions,
    )

    render_before_after(
        export_image,
        "export_comparison",
    )

    st.divider()

    format_col, quality_col = st.columns(2)

    with format_col:
        st.selectbox(
            "Export format",
            ["PNG", "JPEG", "WEBP"],
            key="export_format",
        )

    with quality_col:
        if st.session_state.export_format in (
            "JPEG",
            "WEBP",
        ):
            st.number_input(
                "Image quality",
                min_value=50,
                max_value=100,
                step=1,
                key="export_quality",
            )
        else:
            st.caption(
                "PNG uses lossless compression."
            )

    output = io.BytesIO()

    if st.session_state.export_format == "PNG":
        export_image.save(
            output,
            format="PNG",
            optimize=True,
        )

        mime = "image/png"
        extension = "png"

    elif st.session_state.export_format == "JPEG":
        export_image.convert("RGB").save(
            output,
            format="JPEG",
            quality=int(st.session_state.export_quality),
            optimize=True,
        )

        mime = "image/jpeg"
        extension = "jpg"

    else:
        export_image.save(
            output,
            format="WEBP",
            quality=int(st.session_state.export_quality),
            method=6,
        )

        mime = "image/webp"
        extension = "webp"

    st.download_button(
        "⬇️ Download edited image",
        data=output.getvalue(),
        file_name=(
            f"{st.session_state.image_name}_edited.{extension}"
        ),
        mime=mime,
        type="primary",
        use_container_width=True,
    )

    st.caption(
        f"Final dimensions: {export_image.width:,} × "
        f"{export_image.height:,} pixels"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Pixel Studio · A Photoshop-inspired image editor "
    "built with Streamlit, Pillow, NumPy and OpenCV."
)
