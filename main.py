from demucs.pretrained import get_model
from demucs.apply import apply_model
import librosa
import pathlib
import torch
import soundfile as sf

#uses demucs for now, will create a custom model later on
class vocalRemovalModelHandler:
    def __init__(self,device = "cpu", segment = 8.0):
        self.device = torch.device("cuda" if device == "cuda" and torch.cuda.is_available() else "cpu")
        self.segment = segment
        self.model = get_model("htdemucs_ft")
        self.model = self.model.to(self.device)
        self.model.eval()
        
    def remove_vocals(self, audio_file):
        """Return instrumental using htdemucs_ft model."""
        #it should get the audio from the main, to fix later
        audio, _ = librosa.load(audio_file, sr=self.model.samplerate, mono=False)

        if audio.ndim == 1:
            audio = audio[None, :]

        mix = torch.tensor(audio, dtype=torch.float32, device=self.device)
        #normalize channels to demucs expectations
        if mix.shape[0] == 1:
            mix = mix.repeat(2, 1)
        elif mix.shape[0] > self.model.audio_channels:
            mix = mix[:self.model.audio_channels, :]

        mix = mix.unsqueeze(0)
        with torch.no_grad():
            separated = apply_model(self.model, mix, device=self.device)

        separated = separated[0]
        source_to_stem = {
            source_name: separated[idx]
            for idx, source_name in enumerate(self.model.sources)
        }
        instrumental = mix[0] - source_to_stem["vocals"]

        return instrumental.cpu().numpy()
    
def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    removalHandler = vocalRemovalModelHandler(device=device)
    #it should check here if the file exists and is a valid audio file, but for now it just assumes it is. to fix later
    file = pathlib.Path("plik.wav")
    instrumental = removalHandler.remove_vocals(file)
    sf.write("Hypatia_instrumental_hdemucs.wav", instrumental.T, removalHandler.model.samplerate)

if __name__ == "__main__":
    main()