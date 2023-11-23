create table actors (
  id bigint primary key,
  first_name varchar(100) default null,
  last_name varchar(100) default null,
  gender char(1) default null
);
create index actors_first_name on actors (first_name);
create index actors_last_name on actors (last_name);

--

create table directors (
  id bigint primary key,
  first_name varchar(100) default null,
  last_name varchar(100) default null
);
create index directors_first_name on directors (first_name);
create index directors_last_name on directors (last_name);

--

create table directors_genres (
  director_id bigint not null references directors(id),
  genre varchar(100) not null,
  prob double precision default null,
  primary key (director_id, genre)
);
create index directors_genres_director_id on directors_genres (director_id);

--

create table movies (
  id bigint primary key,
  name varchar(100) default null,
  year smallint default null,
  rank double precision default null
);
create index movies_name on movies (name);

--

create table movies_directors (
  director_id bigint not null references directors(id),
  movie_id bigint not null references movies(id),
  primary key (director_id, movie_id)
);
create index movies_directors_director_id on movies_directors (director_id);
create index movies_directors_movie_id on movies_directors (movie_id);

--

create table movies_genres (
  movie_id bigint not null references movies(id),
  genre varchar(100) not null,
  primary key (movie_id, genre)
);
create index movies_genres_movie_id on movies_genres (movie_id);

--

create table roles (
  actor_id bigint not null references actors(id),
  movie_id bigint not null references movies(id),
  role varchar(100) not null,
  primary key (actor_id, movie_id, role)
);
create index roles_actor_id on roles (actor_id);
create index roles_movie_id on roles (movie_id);
