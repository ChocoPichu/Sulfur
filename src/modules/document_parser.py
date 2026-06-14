import os
import base64
import fitz


def parse_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        text_content = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content.append(page.get_text())
        doc.close()
        return "\n".join(text_content)
    except Exception as e:
        return f"[Error parsing PDF: {e}]"


def encode_image(file_path: str) -> str:
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[SYSTEM] Error encoding image: {e}")
        return ""


def process_file_for_ai(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"type": "error", "content": f"File not found: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)

    if ext == ".pdf":
        return {
            "type": "text",
            "filename": filename,
            "content": (
                f"--- START OF PDF: {filename} ---\n"
                f"{parse_pdf(file_path)}\n--- END OF PDF ---"
            ),
        }

    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        b64_data = encode_image(file_path)
        mime_type = (
            "image/jpeg" if ext in [".jpg", ".jpeg"]
            else f"image/{ext[1:]}"
        )

        return {
            "type": "image",
            "filename": filename,
            "mime_type": mime_type,
            "base64_data": b64_data,
        }

    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return {
                    "type": "text",
                    "filename": filename,
                    "content": (
                        f"--- START OF FILE: {filename} ---\n"
                        f"{f.read()}\n--- END OF FILE ---"
                    ),
                }
        except Exception as e:
            return {
                "type": "error",
                "content": f"Unsupported file format: {filename}",
            }
