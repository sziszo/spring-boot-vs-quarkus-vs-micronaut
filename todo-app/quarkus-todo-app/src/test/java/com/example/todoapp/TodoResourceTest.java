package com.example.todoapp;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.CoreMatchers.is;

@QuarkusTest
public class TodoResourceTest {

  @Test
  public void testListAllTodosEndpoint() {
    given()
            .when().get("/todos")
            .then()
            .statusCode(200)
            .body(
                    containsString("Todo-1"),
                    containsString("Todo-2"),
                    containsString("Todo-3")
            );
  }

}
