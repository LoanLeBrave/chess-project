const express = require('express');
const fs = require('fs');
const cors = require('cors');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

const FILE_PATH = './current_feedback.json';


app.post('/reset', (req, res) => {
  fs.writeFileSync(FILE_PATH, JSON.stringify({}));
  res.json({ message: 'Reset OK' });
});


app.post('/feedback', (req, res) => {
  const feedback = req.body;

  fs.writeFileSync(FILE_PATH, JSON.stringify(feedback, null, 2));

  res.json({ message: 'Feedback sauvegardé' });
});


app.get('/feedback', (req, res) => {
  if (!fs.existsSync(FILE_PATH)) {
    return res.json({});
  }

  const data = JSON.parse(fs.readFileSync(FILE_PATH));
  res.json(data);
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});