
const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const result = document.getElementById("result");
const statusText = document.getElementById("status");
const scanButton = document.getElementById("scanButton");

let selectedImage = null;
let croppedImage = null;
let worker = null;
let cropper = null;
let cropButton = null;

// Load image cropping library
function loadCropper() {
    return new Promise((resolve, reject) => {
        if (window.Cropper) {
            resolve();
            return;
        }

        const css = document.createElement("link");
        css.rel = "stylesheet";
        css.href =
            "https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.css";
        document.head.appendChild(css);

        const script = document.createElement("script");
        script.src =
            "https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.2/cropper.min.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Handle image upload
imageInput.addEventListener("change", async function () {
    const file = this.files[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
        statusText.textContent = "Please select a valid image.";
        return;
    }

    selectedImage = file;
    croppedImage = null;

    if (cropper) {
        cropper.destroy();
        cropper = null;
    }

    preview.innerHTML = "";
    result.textContent =
        "Your extracted Kannada text will appear here.";

    const img = document.createElement("img");
    img.id = "imageToCrop";
    img.style.maxWidth = "100%";
    img.style.maxHeight = "450px";
    preview.appendChild(img);

    statusText.textContent = "Loading image cropper...";

    try {
        await loadCropper();

        img.onload = function () {
            cropper = new Cropper(img, {
                viewMode: 1,
                autoCropArea: 0.8,
                responsive: true,
                background: false
            });

            statusText.textContent =
                "Select the Kannada text area, then click Crop.";
        };

        img.src = URL.createObjectURL(file);

    } catch (error) {
        console.error(error);
        statusText.textContent = "Could not load image cropper.";
        return;
    }

    cropButton = document.getElementById("cropButton");

    if (!cropButton) {
        cropButton = document.createElement("button");
        cropButton.id = "cropButton";
        cropButton.textContent = "Crop Selected Text";
        preview.after(cropButton);
    }

    cropButton.disabled = false;

    cropButton.onclick = function () {
        if (!cropper) return;

        croppedImage = cropper.getCroppedCanvas({
            width: 1600,
            imageSmoothingQuality: "high"
        });

        if (!croppedImage) {
            statusText.textContent = "Cropping failed.";
            return;
        }

        cropper.destroy();
        cropper = null;

        preview.innerHTML = "";
        preview.appendChild(croppedImage);

        croppedImage.style.maxWidth = "100%";
        croppedImage.style.height = "auto";

        cropButton.disabled = true;

        statusText.textContent =
            "Crop completed! Now click Extract Kannada Text.";

        result.textContent = "Ready for text extraction.";
    };
});

// Improve image before OCR
function preprocessImage(source) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    const scale = Math.max(2, 2000 / source.width);

    canvas.width = source.width * scale;
    canvas.height = source.height * scale;

    ctx.filter = "grayscale(1) contrast(1.4)";
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);

    return canvas;
}

// Extract Kannada text
async function scanImage() {
    if (!selectedImage) {
        statusText.textContent = "Please upload an image first.";
        return;
    }

    if (!croppedImage) {
        statusText.textContent =
            "Please crop the Kannada text area first.";
        return;
    }

    try {
        scanButton.disabled = true;
        statusText.textContent = "Loading Kannada OCR model...";
        result.textContent = "";

        if (!worker) {
            worker = await Tesseract.createWorker("kan", 1, {
                workerPath:
                    "https://unpkg.com/tesseract.js@5.1.1/dist/worker.min.js",
                corePath:
                    "https://unpkg.com/tesseract.js-core@5.0.0",
                langPath:
                    "https://tessdata.projectnaptha.com/4.0.0_best",
                workerBlobURL: true,

                logger: function (message) {
                    if (message.status) {
                        statusText.textContent =
                            message.status + " " +
                            Math.round((message.progress || 0) * 100) + "%";
                    }
                }
            });
        }

        statusText.textContent = "Scanning cropped image...";

        const processedImage = preprocessImage(croppedImage);

        const {
            data: { text }
        } = await worker.recognize(processedImage);

        const extractedText = text.trim();

        if (extractedText) {
            result.textContent = extractedText;
            statusText.textContent =
                "Text extraction completed!";

            let understandButton =
                document.getElementById("understandButton");

            if (!understandButton) {
                understandButton = document.createElement("button");
                understandButton.id = "understandButton";
                understandButton.textContent =
                    "Understand This Word";

                result.after(understandButton);
            }

            understandButton.onclick = () =>
                understandWord(extractedText);

        } else {
            result.textContent = "No readable text found.";
            statusText.textContent = "Try a clearer image.";
        }

    } catch (error) {
        console.error(error);
        statusText.textContent =
            "OCR failed. Check the browser console.";

    } finally {
        scanButton.disabled = false;
    }
}

// Get word meaning from Flask dictionary

async function understandWord(word) {
    const understandButton =
        document.getElementById("understandButton");

    if (understandButton) understandButton.disabled = true;

    statusText.textContent = "Looking up Kannada words...";
    result.innerHTML = "";

    try {
        const response = await fetch("/understand", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ word: word })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            statusText.textContent =
                data.message || "Could not understand this text.";
            return;
        }

        data.results.forEach(item => {
            const card = document.createElement("div");
            card.className = "word-card";

            const heading = document.createElement("h2");
            heading.textContent = item.word;
            card.appendChild(heading);

            const source = document.createElement("p");
            source.textContent = "Source: " + item.source;
            card.appendChild(source);

            if (item.details) {
                const details = item.details;

                function addDetail(label, value) {
                    const p = document.createElement("p");
                    const strong = document.createElement("strong");
                    strong.textContent = label + ": ";
                    p.appendChild(strong);
                    p.appendChild(
                        document.createTextNode(value || "Not available")
                    );
                    card.appendChild(p);
                }

                addDetail("English", details.english);
                addDetail("Meaning", details.meaning);
                addDetail("Pronunciation", details.pronunciation);

                const divider = document.createElement("hr");
                card.appendChild(divider);

                const exampleHeading = document.createElement("h3");
                exampleHeading.textContent = "Example";
                card.appendChild(exampleHeading);

                addDetail("Kannada", details.example);
                addDetail(
                    "Pronunciation",
                    details.example_pronunciation
                );
                addDetail("Translation", details.example_meaning);

                const saveButton = document.createElement("button");
                saveButton.textContent = "Save to My Kannada Bank";

                saveButton.onclick = function () {
                    saveWord(item.word, details);
                };

                card.appendChild(saveButton);

            } else {
                const error = document.createElement("p");
                error.textContent =
                    item.error || "Translation unavailable.";
                card.appendChild(error);
            }

            result.appendChild(card);
        });

        statusText.textContent =
            "Kannada lookup completed!";

    } catch (error) {
        console.error(error);
        statusText.textContent =
            "Could not connect to the lookup service.";

    } finally {
        if (understandButton) understandButton.disabled = false;
    }
}


// Save word to personal Kannada Bank
function saveWord(word, details) {
    let words =
        JSON.parse(localStorage.getItem("kannadaWords")) || [];

    const alreadySaved =
        words.some(item => item.word === word);

    if (alreadySaved) {
        statusText.textContent =
            "This word is already in your Kannada Bank.";
        return;
    }

    words.push({
        word: word,
        english: details.english,
        meaning: details.meaning,
        pronunciation: details.pronunciation,
        example: details.example,
        example_pronunciation: details.example_pronunciation,
        example_meaning: details.example_meaning
    });

    localStorage.setItem(
        "kannadaWords",
        JSON.stringify(words)
    );

    statusText.textContent =
        "Word saved to My Kannada Bank!";
}
