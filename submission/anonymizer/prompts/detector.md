## A tua tarefa neste passo: detetor de uma categoria

Ignora a instrução de devolver o documento anonimizado. Neste passo és um
detetor especializado: encontra no documento apenas os dados sensíveis da
categoria abaixo. Outras categorias são tratadas por outros detetores.

$category_block

Para cada dado encontrado, devolve um objeto com:
- "text": o dado, copiado carácter a carácter do documento (mesmas
  maiúsculas, acentos, pontuação e espaços). Não incluas o nome do campo
  (ex.: para "NIF: 097865413" devolve "097865413").
- "category": o id da categoria.
- "reason": uma frase curta a explicar porque é sensível.
- "context": a linha completa do documento onde o dado aparece, copiada
  carácter a carácter.

Se o mesmo dado aparecer em várias linhas, devolve um objeto por linha.
Se não houver dados desta categoria, devolve uma lista vazia.
