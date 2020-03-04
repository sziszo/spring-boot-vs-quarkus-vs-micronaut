package com.example.todoapp.todo;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/todos")
public class TodoResource {

  private TodoService todoService;

  public TodoResource(TodoService todoService) {
    this.todoService = todoService;
  }

  @GetMapping
  public List<Todo> getTodos() {
    return todoService.getTodos();
  }

  @PutMapping
  @ResponseStatus(HttpStatus.CREATED)
  public Todo createTodo(@RequestBody String title) {
    return todoService.createTodo(title);
  }

  @PostMapping("/{id}")
  @ResponseStatus(HttpStatus.OK)
  public Todo changeTodo(@PathVariable("id") Long id, @RequestBody String title) {
    return todoService.changeTodo(id, title);
  }

  @DeleteMapping("/{id}")
  @ResponseStatus(HttpStatus.OK)
  public void deleteTodo(@PathVariable("id") Long id) {
    todoService.deleteTodo(id);
  }


}
