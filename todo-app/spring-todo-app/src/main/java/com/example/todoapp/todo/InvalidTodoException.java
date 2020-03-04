package com.example.todoapp.todo;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.text.MessageFormat;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class InvalidTodoException extends RuntimeException {

  private static final String message = "Invalid todo! id: {0}";

  public InvalidTodoException(Long id) {
    super(MessageFormat.format(message, id));
  }

  public InvalidTodoException(Long id, Throwable cause) {
    super(MessageFormat.format(message, id), cause);
  }
}
