package com.example.todoapp.todo;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class TodoService {

  private TodoRepository todoRepository;

  public TodoService(TodoRepository todoRepository) {
    this.todoRepository = todoRepository;
  }

  @Transactional(readOnly = true)
  public List<Todo> getTodos() {
    return todoRepository.findAll();
  }

  @Transactional
  public Todo createTodo(String title) {

    return todoRepository.save(
            Todo.builder()
                    .title(title)
                    .owner(null)
                    .created(LocalDateTime.now())
                    .build()
    );

  }

  @Transactional
  public Todo changeTodo(Long id, String title) {

    return todoRepository.save(
            todoRepository
                    .findById(id)
                    .map(todo -> {
                      todo.setTitle(title);
                      todo.setModified(LocalDateTime.now());
                      return todo;
                    })
                    .orElseThrow(() -> new InvalidTodoException(id))
    );

  }

  @Transactional
  public void deleteTodo(Long id) {
    try {
      todoRepository.deleteById(id);
    } catch (RuntimeException e) {
      throw new InvalidTodoException(id, e);
    }
  }
}
