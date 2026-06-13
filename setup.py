from setuptools import setup, find_packages

setup(
    name="voice_drawing_tool",
    version="1.0.0",
    description="Voice-controlled drawing tool for Qiniu Cloud 2026 competition",
    author="Suki",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy",
        "opencv-python",
        "Pillow",
        "pypinyin",
        "faster-whisper",
    ],
    extras_require={
        "speech": [
            "SpeechRecognition",
            "pyaudio",
        ],
    },
    entry_points={
        "console_scripts": [
            "voice-drawing=voice_drawing_tool.__main__:main",
        ],
    },
)
