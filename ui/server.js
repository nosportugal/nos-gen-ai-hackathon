const express = require('express');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();

app.use(cors());
app.use(bodyParser.json());

app.post('/run-script', (req, res) => {
  const { arg1, arg2 } = req.body;

  const python = spawn('python3', ['script.py', arg1, arg2]);

  let output = '';
  python.stdout.on('data', (data) => {
    output += data.toString();
  });

  let errorOutput = '';
  python.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });

  python.on('close', (code) => {
    res.json({
      stdout: output,
      stderr: errorOutput,
      exitCode: code
    });
  });
});

app.listen(3000, () => {
  console.log('Server running on http://localhost:3000');
});
