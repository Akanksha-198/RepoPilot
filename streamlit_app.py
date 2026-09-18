import streamlit as st
from pathlib import Path

from app.pipeline import analyze_repository


# ==========================================
# Page configuration
# ==========================================

st.set_page_config(
    page_title="RepoPilot",
    page_icon="🤖",
    layout="wide"
)


# ==========================================
# Header
# ==========================================

st.title("🤖 RepoPilot")

st.markdown(
    """
    ### AI-Powered Repository Analysis

    Connect a GitHub repository, choose where to
    clone it locally, and let RepoPilot understand
    your codebase.
    """
)


st.divider()


# ==========================================
# Repository Configuration
# ==========================================

st.subheader("📦 Repository Configuration")


col1, col2 = st.columns(2)


with col1:

    github_url = st.text_input(
        "🔗 GitHub Repository URL",
        placeholder=(
            "https://github.com/username/repository"
        )
    )


with col2:

    clone_location = st.text_input(
        "📁 Local Clone Location",
        placeholder=(
            r"C:\Users\YourName\Desktop\Repositories"
        )
    )


st.caption(
    "RepoPilot will create the repository folder "
    "inside the location you provide."
)


# ==========================================
# Analyze Button
# ==========================================

analyze_button = st.button(
    "🚀 Analyze Repository",
    type="primary",
    use_container_width=True
)


# ==========================================
# Pipeline
# ==========================================

if analyze_button:

    # Validate GitHub URL

    if not github_url:

        st.warning(
            "Please enter a GitHub repository URL."
        )

        st.stop()


    # Validate clone location

    if not clone_location:

        st.warning(
            "Please enter a local clone location."
        )

        st.stop()


    try:

        # Progress display

        with st.status(
            "🔄 Running RepoPilot...",
            expanded=True
        ):

            st.write(
                "🔍 Reading repository information..."
            )

            st.write(
                "📥 Cloning repository..."
            )

            st.write(
                "🔎 Scanning repository..."
            )

            st.write(
                "🤖 Generating AI overview..."
            )

            result = analyze_repository(
                github_url,
                clone_location
            )

            st.write(
                "✅ Analysis completed."
            )


        st.success(
            "Repository analyzed successfully!"
        )


        # ======================================
        # Repository Information
        # ======================================

        st.header(
            f"📦 {result['repository']}"
        )


        st.info(
            f"📁 Local repository: "
            f"`{result['path']}`"
        )


        scan = result["scan"]


        # ======================================
        # Metrics
        # ======================================

        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "📄 Total Files",
                scan["file_count"]
            )


        with col2:

            st.metric(
                "💻 Languages",
                len(scan["languages"])
            )


        with col3:

            st.metric(
                "⭐ Important Files",
                len(scan["important_files"])
            )


        st.divider()


        # ======================================
        # Languages
        # ======================================

        st.subheader(
            "💻 Detected Languages"
        )


        for language, count in (
            scan["languages"].items()
        ):

            st.write(
                f"**{language}** — {count} files"
            )


        st.divider()


        # ======================================
        # Important Files
        # ======================================

        st.subheader(
            "⭐ Important Files"
        )


        if scan["important_files"]:

            for file in (
                scan["important_files"]
            ):

                st.code(
                    file,
                    language="text"
                )

        else:

            st.caption(
                "No predefined important files detected."
            )


        # ======================================
        # File Tree
        # ======================================

        st.divider()

        st.subheader(
            "📁 Repository File Tree"
        )


        with st.expander(
            "View repository files"
        ):

            for file in scan["files"]:

                st.write(
                    f"📄 `{file}`"
                )


        # ======================================
        # AI Analysis
        # ======================================

        st.divider()

        st.subheader(
            "🤖 RepoPilot AI Analysis"
        )


        st.markdown(
            result["ai_overview"]
        )


    except Exception as error:

        st.error(
            f"❌ Something went wrong:\n\n{error}"
        )