import demucs
import librosa
import pathlib
#uses demucs for now, will create a custom model later on
class vocalRemovalModelHandler:
    def __init__(self):
        self.model = demucs.pretrained.get_model("demucs")

    
    def remove_vocals(self, audio_file):
        """Removes vocals from the given audio file and returns the instrumental version."""
        audio = demucs.audio.load(audio_file)
        stems = self.model.separate(audio)
        return stems["vocals"]
    
def main():
    removalHandler = vocalRemovalModelHandler()
    file = pathlib.Path("Hypatia.mp3")
    mix = librosa.load(file, sr=None)
    instrumental = removalHandler.remove_vocals(mix)
    librosa.output.write_wav("Hypatia_instrumental.wav", instrumental, sr=None)

if __name__ == "__main__":
    main()