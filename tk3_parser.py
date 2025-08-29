import os
import json
import camelot
import fitz
import cv2
import numpy as np
import re
import cloudinary.uploader   # 🔥 import uploader
import cloudinary.api        # optional if you want admin functions
from cloudinary_config import *  # 🔥 load config


def normalize(text):
    return text.strip().lower().replace("–", "-").replace("—", "-")


def extract_qno_from_df(df):
    for row_idx in range(min(3, df.shape[0])):
        cell = str(df.iloc[row_idx, 0]).strip()
        match = re.search(r"\d+", cell)
        if match:
            return int(match.group())
    return None


def process_pdfs(pdf_path, keys_pdf_path, output_dir="table_cropped_folder"):
    try:
        os.makedirs(output_dir, exist_ok=True)

        # ---- STEP 1: Extract keys ----
        print(f"Processing answer key PDF: {keys_pdf_path}")
        keys_tables = camelot.read_pdf(
            keys_pdf_path, pages="all", flavor="lattice")
        keys_data = {}
        saved_qno_idx = saved_qtype_idx = saved_key_idx = None

        for table in keys_tables:
            df = table.df
            if df.empty:
                continue

            headers = [normalize(str(h)) for h in df.iloc[0]]

            if any("q. no" in h or "q no" in h or "question" in h for h in headers):
                def find_col(name_parts):
                    for idx, col in enumerate(headers):
                        if any(part in col for part in name_parts):
                            return idx
                    return None

                try:
                    saved_qno_idx = find_col(["q. no", "q no", "question"])
                    saved_qtype_idx = find_col(["q. type", "type", "q type"])
                    saved_key_idx = find_col(
                        ["key/range", "key", "answer", "range"])

                    if saved_qno_idx is None:
                        continue
                except Exception as e:
                    print(f"Error finding columns: {e}")
                    continue
                start_row = 1
            else:
                if saved_qno_idx is None:
                    continue
                start_row = 0

            for i in range(start_row, len(df)):
                try:
                    q_no_val = str(df.iloc[i, saved_qno_idx]).strip()
                    match = re.search(r"\d+", q_no_val)
                    if not match:
                        continue

                    q_no = int(match.group())
                    q_type = str(df.iloc[i, saved_qtype_idx]).strip(
                    ) if saved_qtype_idx is not None else "MCQ"
                    answer = str(df.iloc[i, saved_key_idx]).strip(
                    ) if saved_key_idx is not None else ""

                    if answer and answer != "nan":
                        keys_data[q_no] = {"type": q_type, "answer": answer}

                except Exception as e:
                    print(f"Error processing row {i}: {e}")
                    continue

        print(f"Extracted {len(keys_data)} answer keys")

        # ---- STEP 2: Extract questions ----
        print(f"Processing question PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        results = []

        for page_num in range(len(doc)):
            page_number = page_num + 1
            print(f"Processing page {page_number}")

            try:
                tables = camelot.read_pdf(
                    pdf_path, pages=str(page_number), flavor='lattice')

                if tables.n > 0:
                    pix = doc[page_num].get_pixmap(dpi=300)
                    image = np.frombuffer(pix.tobytes(), np.uint8)
                    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

                    page_width = doc[page_num].rect.width
                    page_height = doc[page_num].rect.height

                    for idx, table in enumerate(tables):
                        if table.df.empty:
                            continue

                        x1, y1, x2, y2 = table._bbox
                        img_x1 = int(x1 * pix.width / page_width)
                        img_x2 = int(x2 * pix.width / page_width)
                        img_y1 = int((page_height - y2) *
                                     pix.height / page_height)
                        img_y2 = int((page_height - y1) *
                                     pix.height / page_height)

                        if img_x2 - img_x1 > 5 and img_y2 - img_y1 > 5 and img_x1 >= 0 and img_y1 >= 0:
                            q_no_found = extract_qno_from_df(table.df)

                            # Save temporary local image
                            table_img_path = os.path.join(
                                output_dir, f"page_{page_number}_table_{idx+1}.png")
                            try:
                                cropped = image[img_y1:img_y2, img_x1:img_x2]
                                cv2.imwrite(table_img_path, cropped)

                                # 🔥 Upload to Cloudinary
                                upload_result = cloudinary.uploader.upload(
                                    table_img_path,
                                    folder="gate_papers/questions"  # optional folder in Cloudinary
                                )
                                cloud_url = upload_result["secure_url"]

                                # Remove local file after upload
                                os.remove(table_img_path)

                            except Exception as e:
                                print(f"Error saving/uploading image: {e}")
                                continue

                            q_data = {
                                "q_no": q_no_found,
                                "image_path": cloud_url,  # 🔥 Save Cloudinary URL instead of local path
                                "question_type": "MCQ",
                                "correct_answers": None,
                                "range_min": None,
                                "range_max": None
                            }

                            if q_no_found and q_no_found in keys_data:
                                key_info = keys_data[q_no_found]
                                q_data["question_type"] = key_info["type"]

                                answer = key_info["answer"]
                                if "-" in answer and any(c.isdigit() for c in answer):
                                    try:
                                        parts = answer.split("-")
                                        if len(parts) == 2:
                                            q_data["range_min"] = float(
                                                parts[0].strip())
                                            q_data["range_max"] = float(
                                                parts[1].strip())
                                            q_data["question_type"] = "NAT"
                                    except (ValueError, IndexError):
                                        q_data["correct_answers"] = [answer]
                                else:
                                    q_data["correct_answers"] = [answer]

                            results.append(q_data)

            except Exception as e:
                print(f"Error processing page {page_number}: {e}")
                continue

        doc.close()
        print(f"Extracted {len(results)} questions")
        return results

    except Exception as e:
        print(f"Error in process_pdfs: {e}")
        return []
