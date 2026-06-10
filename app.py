import datetime
import streamlit as st
from supabase import create_client, Client

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET_NAME = "audio_uploads"

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

st.title("Audio Uploader to Supabase")

st.markdown(
    "Upload large amounts of audio files and store them in a structured way in Supabase Storage."
)

# ---------- METADATA FORM ----------
with st.form("metadata_form"):
    observer = st.text_input("Observer name")
    obs_date = st.date_input("Observation date", value=datetime.date.today())
    area = st.text_input("Area / Zone")
    files = st.file_uploader(
        "Select audio files",
        type=["wav", "mp3", "flac", "m4a", "ogg"],
        accept_multiple_files=True,
    )
    submitted = st.form_submit_button("Upload")

if submitted:
    if not observer or not area:
        st.error("Please fill in observer and area.")
    elif not files:
        st.error("Please select at least one audio file.")
    else:
        # Create subfolder name: YYYY-MM-DD_area_observer
        folder_name = (
            f"{obs_date.isoformat()}_"
            f"{area.strip().replace(' ', '-')}_"
            f"{observer.strip().replace(' ', '-')}"
        )
        st.write(f"Subfolder: `{folder_name}`")

        upload_results = []

        for f in files:
            st.write(f"Uploading **{f.name}**...")
            progress = st.progress(0)

            file_path = f"{folder_name}/{f.name}"

            try:
                # Visual progress (Supabase upload is atomic)
                progress.progress(25)

                supabase.storage.from_(BUCKET_NAME).upload(
                    file_path,
                    f.getvalue(),
                    {"content-type": f.type or "application/octet-stream"},
                )

                progress.progress(75)

                # Insert metadata row
                data = {
                    "observer": observer,
                    "area": area,
                    "obs_date": obs_date.isoformat(),
                    "file_name": f.name,
                    "path": file_path,
                    "bucket": BUCKET_NAME,
                }
                supabase.table("audio_files").insert(data).execute()

                progress.progress(100)
                upload_results.append((f.name, "OK"))

            except Exception as e:
                progress

