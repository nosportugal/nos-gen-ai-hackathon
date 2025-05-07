const form = document.querySelector("form")


form.addEventListener("submit", async (ev) => {
  ev.preventDefault()

  const inputFile = document.querySelector("#inputFile")

  const nome = inputFile.files[0].name

  console.log(nome);


  const res = await fetch('http://localhost:3000/run-script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ arg1: nome, arg2: nome })
  });

  const data = await res.json();
  console.log('Python output:', data.stdout);


})
