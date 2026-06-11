import datetime
import streamlit as st
from supabase import create_client, Client
import io
import zipfile

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET_NAME = "audio_uploads"

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ---------- NAVIGATION ----------
mode = st.radio("Choose mode", ["Upload", "Explore"])

# ============================================================
# ========================= UPLOAD ============================
# ============================================================

if mode == "Upload":

    st.title("Audio Uploader to Supabase")

    st.markdown(
        "Upload large amounts of audio files and store them in a structured way in Supabase Storage."
    )

    OBSERVERS = ["Max", "Mats", "Jan", "Rep", "Guido", "Luigi", "Wout"]
    AREAS = ["Z1", "Z2/3", "Z4", "Z5", "Z6/7", "Z8", "Z9", "Z10a", "Z10b", "Z11", "Z12", "Z13"]

    with st.form("metadata_form"):
        observer = st.selectbox("Observer name", OBSERVERS)
        obs_date = st.date_input("Observation date", value=datetime.date.today())
        area = st.selectbox("Area / Zone", AREAS)

        files = st.file_uploader(
            "Select audio files",
            type=["wav", "mp3", "flac", "m4a", "ogg"],
            accept_multiple_files=True,
        )

        submitted = st.form_submit_button("Upload")

    if submitted:
        if not files:
            st.error("Please select at least one audio file.")
        else:
            folder_name = (
                f"{obs_date.isoformat()}_"
                f"{area.replace(' ', '-')}_"
                f"{observer.replace(' ', '-')}"
            )
            st.write(f"Subfolder: `{folder_name}`")

            upload_results = []

            for f in files:
                st.write(f"Uploading **{f.name}**...")
                progress = st.progress(0)

                file_path = f"{folder_name}/{f.name}"
                file_bytes = f.getvalue()

                try:
                    progress.progress(25)

                    supabase.storage.from_(BUCKET_NAME).upload(
                        file_path,
                        file_bytes,
                        {"content-type": f.type or "application/octet-stream"},
                    )

                    progress.progress(75)

                    data = {
                        "observer": observer,
                        "area": area,
                        "obs_date": obs_date.isoformat(),
                        "file_name": f.name,
                        "path": file_path,
                        "bucket": BUCKET_NAME,
                        "size_bytes": len(file_bytes),  # store size for fast filtering
                    }
                    supabase.table("audio_files").insert(data).execute()

                    progress.progress(100)
                    upload_results.append((f.name, "OK"))

                except Exception as e:
                    progress.progress(100)
                    st.error(f"Error with {f.name}: {e}")
                    upload_results.append((f.name, "Error"))

            if upload_results:
                st.success("Upload finished.")
                for name, status in upload_results:
                    st.write(f"- {name}: {status}")



# ============================================================
# ========================= EXPLORE ===========================
# ============================================================

if mode == "Explore":

    st.title("Explore Uploaded Audio Files")

    rows = supabase.table("audio_files").select("*").execute().data

    if not rows:
        st.info("No files uploaded yet.")
        st.stop()

    # ---------- CASCADE FILTERING ----------

    # 1. AREA
    all_areas = sorted({r["area"] for r in rows})
    selected_areas = st.multiselect("Select Area(s)", all_areas)

    filtered = rows
    if selected_areas:
        filtered = [r for r in filtered if r["area"] in selected_areas]

    # 2. OBSERVER
    all_observers = sorted({r["observer"] for r in filtered})
    selected_observers = st.multiselect("Select Observer(s)", all_observers)

    if selected_observers:
        filtered = [r for r in filtered if r["observer"] in selected_observers]

    # 3. DATE
    all_dates = sorted({r["obs_date"] for r in filtered})
    selected_dates = st.multiselect("Select Date(s)", all_dates)

    if selected_dates:
        filtered = [r for r in filtered if r["obs_date"] in selected_dates]

    # ---------- SUMMARY ----------
    st.subheader("Summary")
    st.write(f"**Files found:** {len(filtered)}")

    total_bytes = sum(r.get("size_bytes", 0) or 0 for r in filtered)
    total_mb = round(total_bytes / (1024 * 1024), 2)
    st.write(f"**Total size:** {total_mb} MB")

    st.divider()

    # ---------- DOWNLOAD SELECTED FILES ----------
    st.subheader("Download Selected Files")

    if st.button("Prepare ZIP file"):
        if not filtered:
            st.warning("No files to download.")
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for r in filtered:
                    file_bytes = supabase.storage.from_(BUCKET_NAME).download(r["path"])
                    zipf.writestr(r["file_name"], file_bytes)

            st.success("ZIP ready!")

            st.download_button(
                label="Download ZIP",
                data=zip_buffer.getvalue(),
                file_name="audio_files.zip",
            )


        def get_bucket_size(bucket_name):
            # List all files in the bucket (recursively)
            files = supabase.storage.from_(bucket_name).list("", {"recursive": True})
        
            total_bytes = 0
            for f in files:
                if "metadata" in f and "size" in f["metadata"]:
                    total_bytes += f["metadata"]["size"]
        
            return total_bytes
        
        size_bytes = get_bucket_size("my-bucket")
        print("Total size:", size_bytes, "bytes")
        print("Total size (MB):", size_bytes / (1024 * 1024))






