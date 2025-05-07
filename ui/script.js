const form = document.querySelector("form")


form.addEventListener("submit", async (ev) => {
  ev.preventDefault()

  const inputFile = document.querySelector("#inputFile")

  const nome = inputFile.files[0].name

  console.log(nome);


  const res = await fetch('http://localhost:3000/run-script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      arg1: nome, arg2: document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById('inputFile');
        const file = fileInput.files[0];
        if (!file) return alert('Selecione um ficheiro PDF');

        const formData = new FormData();
        formData.append('ficheiro', file);

        const response = await fetch('http://localhost:3000/run-script', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        const outputEl = document.getElementById('outputText');
        if (data.error) {
          outputEl.textContent = 'Erro: ' + data.error;
        } else {
          outputEl.textContent = data.result;
        }
      })
    })
  });

  const data = await res.json();
  console.log('Python output:', data.stdout);

  outputEl = document.getElementById('outputText');

  outputEl.innerHTML = data.stdout;

})
