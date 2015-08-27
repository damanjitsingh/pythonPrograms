'''
some sql commands from https://www.youtube.com/watch?v=Thd8yoBou7k

1. select title,year from movie where title='Ring'
2. select count(*) from movie where title like '%batman%'
3. select title,year from movie order by length(year) asc limit 5;
 select title from movie where title like '%fun%' limit 5; 
4. select count(*) from actor group by gender
# difference between below 2 statements:
select avg(blood_pressure) as bp from company having bp>120;
select avg(blood_pressure) as bp from company where bp>120;
In the second statement where clause can only be applied with table entries and not on aggregates like sum, avg etc.
problem from link: https://github.com/brandon-rhodes/pycon-sql-tutorial/blob/master/exercises.rst
4.3 what is the most common movie ever
select count(*) as ct,title from movie group by title order by ct desc limit 1; 
'''

'''
insert, update and delete statements
begin;
insert into movie (title,year) values ('foo',2012);
commit;
'''

